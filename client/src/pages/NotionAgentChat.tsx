import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { createThread, type AgentStep } from "../api/rag";
import {
  getNotionSources,
  sendNotionAgentMessage,
  syncNotionMemory,
  type NotionSourceChunk,
  type NotionSourcePage,
} from "../api/notionAgent";

type NotionMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: NotionSourceChunk[];
  agentSteps?: AgentStep[];
};

const getClientId = () => {
  const key = "notion_agent_client_id";
  const existing = window.localStorage.getItem(key);
  if (existing) {
    return existing;
  }
  const next = crypto.randomUUID();
  window.localStorage.setItem(key, next);
  return next;
};

const formatDate = (value: string | null) => {
  if (!value) {
    return "No edit time";
  }
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
};

function NotionAgentChat() {
  const clientId = useMemo(getClientId, []);
  const [threadId, setThreadId] = useState<string | null>(null);
  const [sources, setSources] = useState<NotionSourcePage[]>([]);
  const [messages, setMessages] = useState<NotionMessage[]>([]);
  const [input, setInput] = useState("");
  const [status, setStatus] = useState("Connecting to Notion memory...");
  const [isSyncing, setIsSyncing] = useState(false);
  const [isSending, setIsSending] = useState(false);

  const refreshSources = async () => {
    const nextSources = await getNotionSources();
    setSources(nextSources);
    return nextSources;
  };

  useEffect(() => {
    const boot = async () => {
      const [thread, nextSources] = await Promise.all([
        createThread(clientId, "Notion memory chat"),
        refreshSources(),
      ]);
      setThreadId(thread.thread_id);
      setStatus(
        nextSources.length > 0
          ? `${nextSources.length} Notion pages are indexed.`
          : "No Notion pages indexed yet. Run sync after sharing pages with the integration.",
      );
    };

    boot().catch(() => {
      setStatus("Could not reach the Notion agent backend.");
    });
  }, [clientId]);

  const handleSync = async () => {
    if (isSyncing) {
      return;
    }

    setIsSyncing(true);
    setStatus("Syncing shared Notion pages...");
    try {
      const result = await syncNotionMemory();
      const nextSources = await refreshSources();
      setStatus(
        `${result.message} ${nextSources.length} pages available for chat.`,
      );
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Notion sync failed.");
    } finally {
      setIsSyncing(false);
    }
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const message = input.trim();
    if (!message || !threadId || isSending) {
      return;
    }

    setMessages((current) => [
      ...current,
      {
        id: crypto.randomUUID(),
        role: "user",
        content: message,
      },
    ]);
    setInput("");
    setIsSending(true);
    setStatus("Retriever, Answerer, and Critic are checking Notion memory...");

    try {
      const response = await sendNotionAgentMessage(threadId, clientId, message);
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
      setStatus(
        response.sources.length > 0
          ? `Answer ready with ${response.sources.length} Notion sources.`
          : "Answer ready. No matching Notion chunks were found.",
      );
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Notion chat failed.");
    } finally {
      setIsSending(false);
    }
  };

  return (
    <main className="support-page notion-page">
      <section className="support-workspace">
        <div>
          <p className="eyebrow">Notion Memory Route</p>
          <h1>Ask your Notion notes</h1>
          <p className="support-subtitle">
            Shared Notion pages are indexed into a separate memory collection and
            answered through a Retriever, Answerer, and Critic graph.
          </p>
          <Link className="notion-back-link" to="/">
            Back to document chat
          </Link>
        </div>

        <div className="support-documents">
          <div className="list-header">
            <h2>Notion sources</h2>
            <span>{sources.length}</span>
          </div>
          {sources.length === 0 ? (
            <p>No Notion pages indexed yet.</p>
          ) : (
            sources.slice(0, 6).map((source) => (
              <a
                className="support-document notion-source-item"
                href={source.url}
                key={source.page_id}
                rel="noreferrer"
                target="_blank"
              >
                <strong>{source.page_title}</strong>
                <span>
                  {source.chunk_count} chunks | edited {formatDate(source.last_edited_time)}
                </span>
              </a>
            ))
          )}
          <button
            className="support-upload notion-sync-button"
            disabled={isSyncing}
            onClick={handleSync}
            type="button"
          >
            {isSyncing ? "Syncing..." : "Sync Notion"}
          </button>
        </div>
      </section>

      <section className="support-popup" aria-label="Notion memory chat">
        <header className="support-popup-header">
          <div>
            <strong>Notion memory</strong>
            <span>{status}</span>
          </div>
          <span className="support-live-dot" />
        </header>

        <div className="support-messages">
          {messages.length === 0 ? (
            <div className="support-empty">
              <h2>Ask from your notes</h2>
              <p>
                Try decisions, architecture notes, meeting takeaways, or anything
                you remember writing but cannot place.
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
                    <summary>Notion sources</summary>
                    {message.sources.map((source) => (
                      <div key={`${source.page_id}-${source.chunk_index}`}>
                        <strong>{source.page_title}</strong>
                        <span>
                          Chunk {source.chunk_index} | score {source.score.toFixed(2)}
                        </span>
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
            placeholder="Ask about your Notion notes..."
            disabled={!threadId || isSending}
          />
          <button type="submit" disabled={!threadId || isSending || !input.trim()}>
            {isSending ? "Checking" : "Send"}
          </button>
        </form>
      </section>
    </main>
  );
}

export default NotionAgentChat;
