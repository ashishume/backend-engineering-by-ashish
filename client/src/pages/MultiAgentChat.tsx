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
  getRagDocuments,
  sendMultiAgentMessage,
  uploadRagDocument,
  type AgentStep,
  type RagDocument,
  type SourceChunk,
} from "../api/rag";

type SupportMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: SourceChunk[];
  agentSteps?: AgentStep[];
};

const getClientId = () => {
  const key = "multi_agent_client_id";
  const existing = window.localStorage.getItem(key);
  if (existing) {
    return existing;
  }
  const next = crypto.randomUUID();
  window.localStorage.setItem(key, next);
  return next;
};

function MultiAgentChat() {
  const clientId = useMemo(getClientId, []);
  const [threadId, setThreadId] = useState<string | null>(null);
  const [documents, setDocuments] = useState<RagDocument[]>([]);
  const [messages, setMessages] = useState<SupportMessage[]>([]);
  const [input, setInput] = useState("");
  const [status, setStatus] = useState("Customer support team is ready.");
  const [isUploading, setIsUploading] = useState(false);
  const [isSending, setIsSending] = useState(false);

  useEffect(() => {
    const boot = async () => {
      const [thread, nextDocuments] = await Promise.all([
        createThread(clientId, "Multi-agent support"),
        getRagDocuments(),
      ]);
      setThreadId(thread.thread_id);
      setDocuments(nextDocuments);
    };

    boot().catch(() => {
      setStatus("Could not reach the AI agent backend.");
    });
  }, [clientId]);

  const handleUpload = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }

    setIsUploading(true);
    setStatus(`Indexing ${file.name} for support retrieval...`);
    try {
      await uploadRagDocument(file, true);
      setDocuments(await getRagDocuments());
      setStatus(`${file.name} is available to the Knowledge Agent.`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Document upload failed.");
    } finally {
      event.target.value = "";
      setIsUploading(false);
    }
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const message = input.trim();
    if (!message || !threadId || isSending) {
      return;
    }

    const userMessage: SupportMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: message,
    };
    setMessages((current) => [...current, userMessage]);
    setInput("");
    setIsSending(true);
    setStatus("Agents are working on the customer query...");

    try {
      const response = await sendMultiAgentMessage(threadId, clientId, message);
      setThreadId(response.thread_id);
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: response.answer,
          sources: response.sources,
          agentSteps: response.agent_steps,
        },
      ]);
      setStatus("Response ready.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Multi-agent chat failed.");
    } finally {
      setIsSending(false);
    }
  };

  return (
    <main className="support-page">
      <section className="support-workspace">
        <div>
          <p className="eyebrow">LangGraph Multi-Agent Route</p>
          <h1>Customer support cockpit</h1>
          <p className="support-subtitle">
            Intake, Knowledge, Resolution, and Quality agents collaborate on each reply.
          </p>
        </div>

        <div className="support-documents">
          <div className="list-header">
            <h2>Retrieval documents</h2>
            <span>{documents.length}</span>
          </div>
          {documents.length === 0 ? (
            <p>No documents indexed yet.</p>
          ) : (
            documents.slice(0, 4).map((document) => (
              <div className="support-document" key={document.document_id}>
                <strong>{document.filename}</strong>
                <span>{document.chunk_count} chunks</span>
              </div>
            ))
          )}
          <label className="support-upload">
            <input
              type="file"
              accept=".pdf,.txt,.md"
              onChange={handleUpload}
              disabled={isUploading}
            />
            <span>{isUploading ? "Indexing..." : "Upload policy or FAQ"}</span>
          </label>
        </div>
      </section>

      <section className="support-popup" aria-label="Multi-agent customer chat">
        <header className="support-popup-header">
          <div>
            <strong>Support agents</strong>
            <span>{status}</span>
          </div>
          <span className="support-live-dot" />
        </header>

        <div className="support-messages">
          {messages.length === 0 ? (
            <div className="support-empty">
              <h2>Ask a customer query</h2>
              <p>
                Try refund policies, troubleshooting, document-specific questions, or
                requests that need a careful handoff-style answer.
              </p>
            </div>
          ) : (
            messages.map((message) => (
              <article className={`support-message ${message.role}`} key={message.id}>
                {message.role === "assistant" ? (
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {message.content}
                  </ReactMarkdown>
                ) : (
                  <p>{message.content}</p>
                )}

                {message.agentSteps && message.agentSteps.length > 0 && (
                  <details className="agent-trace">
                    <summary>Agent work</summary>
                    {message.agentSteps.map((step) => (
                      <div key={`${message.id}-${step.agent}`}>
                        <strong>{step.agent}</strong>
                        <span>{step.task}</span>
                        <p>{step.output}</p>
                      </div>
                    ))}
                  </details>
                )}

                {message.sources && message.sources.length > 0 && (
                  <details className="agent-trace">
                    <summary>Sources</summary>
                    {message.sources.map((source) => (
                      <div key={`${source.document_id}-${source.chunk_index}`}>
                        <strong>{source.filename}</strong>
                        <span>Chunk {source.chunk_index} | score {source.score.toFixed(2)}</span>
                        <p>{source.text}</p>
                      </div>
                    ))}
                  </details>
                )}
              </article>
            ))
          )}
        </div>

        <form className="support-form" onSubmit={handleSubmit}>
          <input
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Describe the customer issue..."
            disabled={!threadId || isSending}
          />
          <button type="submit" disabled={!threadId || isSending || !input.trim()}>
            {isSending ? "Working" : "Send"}
          </button>
        </form>
      </section>
    </main>
  );
}

export default MultiAgentChat;
