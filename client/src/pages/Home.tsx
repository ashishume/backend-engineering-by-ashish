import {
  useEffect,
  useMemo,
  useState,
  type ChangeEvent,
  type FormEvent,
} from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  createThread,
  deleteRagDocument,
  getRagDocuments,
  getThreadMessages,
  getThreads,
  streamRagMessage,
  uploadRagDocument,
  type ChatThread,
  type RagDocument,
  type SourceChunk,
} from "../api/rag";

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  mode?: "rag" | "general";
  sources?: SourceChunk[];
};

const getSessionId = () => {
  const key = "rag_client_id";
  const existing = window.localStorage.getItem(key);
  if (existing) {
    return existing;
  }
  const next = crypto.randomUUID();
  window.localStorage.setItem(key, next);
  return next;
};

function Home() {
  const clientId = useMemo(getSessionId, []);
  const [documents, setDocuments] = useState<RagDocument[]>([]);
  const [threads, setThreads] = useState<ChatThread[]>([]);
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [useLangchain, setUseLangchain] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const [status, setStatus] = useState("Upload a document, then ask about it.");

  const refreshDocuments = async () => {
    const nextDocuments = await getRagDocuments();
    setDocuments(nextDocuments);
  };

  const refreshThreads = async () => {
    const nextThreads = await getThreads(clientId);
    setThreads(nextThreads);
    return nextThreads;
  };

  const loadThreadMessages = async (threadId: string) => {
    const persistedMessages = await getThreadMessages(threadId);
    setMessages(
      persistedMessages.map((message) => ({
        id: String(message.id),
        role: message.role,
        content: message.content,
        mode: message.mode ?? undefined,
      })),
    );
  };

  const openThread = async (threadId: string) => {
    setActiveThreadId(threadId);
    await loadThreadMessages(threadId);
  };

  const createNewThread = async () => {
    const thread = await createThread(clientId);
    setThreads((current) => [thread, ...current]);
    setActiveThreadId(thread.thread_id);
    setMessages([]);
    setStatus("New thread ready.");
  };

  useEffect(() => {
    const hydrateWorkspace = async () => {
      await refreshDocuments();
      const nextThreads = await refreshThreads();
      if (nextThreads.length > 0) {
        setActiveThreadId(nextThreads[0].thread_id);
        await loadThreadMessages(nextThreads[0].thread_id);
      } else {
        const thread = await createThread(clientId, "New chat");
        setThreads([thread]);
        setActiveThreadId(thread.thread_id);
      }
    };

    hydrateWorkspace().catch(() => {
      setStatus("Could not reach the RAG backend at the configured API URL.");
    });
  }, [clientId]);

  const handleUpload = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }

    setIsUploading(true);
    setStatus(
      `Indexing ${file.name} with ${
        useLangchain ? "LangChain/LangGraph" : "manual"
      } engine...`,
    );
    try {
      await uploadRagDocument(file, useLangchain);
      await refreshDocuments();
      setStatus(`${file.name} is indexed and ready.`);
    } catch (error) {
      setStatus(
        error instanceof Error ? error.message : "Document upload failed.",
      );
    } finally {
      event.target.value = "";
      setIsUploading(false);
    }
  };

  const handleDelete = async (documentId: string) => {
    await deleteRagDocument(documentId);
    await refreshDocuments();
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const question = input.trim();
    if (!question || isThinking || !activeThreadId) {
      return;
    }

    setInput("");
    setIsThinking(true);
    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: question,
    };
    const assistantMessageId = crypto.randomUUID();
    const assistantMessage: ChatMessage = {
      id: assistantMessageId,
      role: "assistant",
      content: "",
    };
    setMessages((current) => [...current, userMessage, assistantMessage]);

    try {
      await streamRagMessage(activeThreadId, clientId, question, useLangchain, {
        onMetadata: (metadata) => {
          if (metadata.thread_id !== activeThreadId) {
            setActiveThreadId(metadata.thread_id);
          }
          setMessages((current) =>
            current.map((messageItem) =>
              messageItem.id === assistantMessageId
                ? {
                    ...messageItem,
                    mode: metadata.mode,
                    sources: metadata.sources,
                  }
                : messageItem,
            ),
          );
          setStatus(
            metadata.mode === "rag"
              ? `Streaming ${useLangchain ? "LangChain/LangGraph" : "manual"} answer with document context.`
              : `Streaming a ${
                  useLangchain ? "LangChain/LangGraph" : "manual"
                } general answer because no strong document match was found.`,
          );
        },
        onToken: (token) => {
          setMessages((current) =>
            current.map((messageItem) =>
              messageItem.id === assistantMessageId
                ? { ...messageItem, content: `${messageItem.content}${token}` }
                : messageItem,
            ),
          );
        },
        onDone: async () => {
          setStatus("Answer complete.");
          await refreshThreads();
        },
      });
    } catch (error) {
      setStatus(
        error instanceof Error ? error.message : "Chat request failed.",
      );
      setMessages((current) =>
        current.map((messageItem) =>
          messageItem.id === assistantMessageId && !messageItem.content
            ? { ...messageItem, content: "The streaming response failed." }
            : messageItem,
        ),
      );
    } finally {
      setIsThinking(false);
    }
  };

  return (
    <main className="rag-shell">
      <section className="rag-sidebar">
        <div>
          <p className="eyebrow">RAG Workspace</p>
          <h1>Document chat</h1>
          <p className="status-text">{status}</p>
        </div>

        <div className="thread-list">
          <div className="list-header">
            <h2>Threads</h2>
            <button type="button" onClick={createNewThread}>
              New
            </button>
          </div>
          {threads.map((thread) => (
            <button
              className={`thread-item ${
                thread.thread_id === activeThreadId ? "active" : ""
              }`}
              key={thread.thread_id}
              onClick={() => openThread(thread.thread_id)}
              type="button"
            >
              <span>{thread.title}</span>
            </button>
          ))}
        </div>

        <label className="upload-box">
          <input
            type="file"
            accept=".pdf,.txt,.md"
            onChange={handleUpload}
            disabled={isUploading}
          />
          <span>{isUploading ? "Indexing..." : "Upload PDF, TXT, or MD"}</span>
        </label>

        <label className="engine-toggle">
          <input
            type="checkbox"
            checked={useLangchain}
            onChange={(event) => setUseLangchain(event.target.checked)}
            disabled={isThinking || isUploading}
          />
          <span>
            <strong>
              {useLangchain ? "LangChain/LangGraph" : "Manual engine"}
            </strong>
            <small>
              {useLangchain
                ? "Uses the parallel implementation in ai-agent/app/langchain_rag."
                : "Uses your original RagService implementation."}
            </small>
          </span>
        </label>

        <div className="document-list">
          <div className="list-header">
            <h2>Indexed documents</h2>
            <button type="button" onClick={refreshDocuments}>
              Refresh
            </button>
          </div>
          {documents.length === 0 ? (
            <p className="empty-text">No documents indexed yet.</p>
          ) : (
            documents.map((document) => (
              <article className="document-item" key={document.document_id}>
                <div>
                  <strong>{document.filename}</strong>
                  <span>
                    {document.chunk_count} chunks ·{" "}
                    {document.source_type.toUpperCase()}
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => handleDelete(document.document_id)}
                >
                  Delete
                </button>
              </article>
            ))
          )}
        </div>
      </section>

      <section className="chat-panel">
        <div className="messages">
          {messages.length === 0 ? (
            <div className="empty-chat">
              <h2>Ask anything</h2>
              <p>
                Related questions use your indexed documents. Unrelated
                questions get a regular assistant answer.
              </p>
            </div>
          ) : (
            messages.map((message) => (
              <article className={`message ${message.role}`} key={message.id}>
                <div className="message-body">
                  {message.role === "assistant" ? (
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {message.content || " "}
                    </ReactMarkdown>
                  ) : (
                    message.content
                  )}
                </div>
                {message.role === "assistant" && (
                  <div className="message-meta">
                    {message.mode
                      ? message.mode === "rag"
                        ? "RAG answer"
                        : "General answer"
                      : "Streaming..."}
                  </div>
                )}
                {message.sources && message.sources.length > 0 && (
                  <div className="sources">
                    {message.sources.map((source) => (
                      <details
                        key={`${source.document_id}-${source.chunk_index}`}
                      >
                        <summary>
                          {source.filename} · chunk {source.chunk_index} · score{" "}
                          {source.score.toFixed(2)}
                        </summary>
                        <p>{source.text}</p>
                      </details>
                    ))}
                  </div>
                )}
              </article>
            ))
          )}
        </div>

        <form className="chat-form" onSubmit={handleSubmit}>
          <input
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Ask about your document or anything else..."
            disabled={isThinking || !activeThreadId}
          />
          <button
            type="submit"
            disabled={isThinking || !input.trim() || !activeThreadId}
          >
            {isThinking ? "Thinking" : "Send"}
          </button>
        </form>
      </section>
    </main>
  );
}

export default Home;
