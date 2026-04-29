import axios from "axios";

const AI_AGENT_BASE_URL = import.meta.env.VITE_AI_AGENT_API_URL || "http://localhost:8001";

const ragApi = axios.create({
  baseURL: AI_AGENT_BASE_URL,
});

export type RagDocument = {
  document_id: string;
  filename: string;
  source_type: string;
  chunk_count: number;
  created_at: string;
};

export type SourceChunk = {
  document_id: string;
  filename: string;
  chunk_index: number;
  text: string;
  score: number;
};

export type RagChatResponse = {
  answer: string;
  mode: "rag" | "general";
  sources: SourceChunk[];
  session_id: string;
  thread_id: string;
};

export type ChatThread = {
  thread_id: string;
  client_id: string;
  title: string;
  created_at: string;
  updated_at: string;
};

export type PersistedChatMessage = {
  id: number;
  thread_id: string;
  role: "user" | "assistant";
  content: string;
  mode: "rag" | "general" | null;
  created_at: string;
};

type StreamMetadata = {
  mode: "rag" | "general";
  sources: SourceChunk[];
  session_id: string;
  thread_id: string;
};

type StreamCallbacks = {
  onMetadata: (metadata: StreamMetadata) => void;
  onToken: (token: string) => void;
  onDone: (answer: string) => void;
};

export const uploadRagDocument = async (
  file: File,
  useLangchain = false,
): Promise<RagDocument> => {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("use_langchain", String(useLangchain));

  const response = await ragApi.post<{ document: RagDocument }>("/rag/documents", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data.document;
};

export const getRagDocuments = async (): Promise<RagDocument[]> => {
  const response = await ragApi.get<{ documents: RagDocument[] }>("/rag/documents");
  return response.data.documents;
};

export const deleteRagDocument = async (documentId: string): Promise<void> => {
  await ragApi.delete(`/rag/documents/${documentId}`);
};

export const sendRagMessage = async (
  threadId: string,
  clientId: string,
  message: string,
  useLangchain = false,
): Promise<RagChatResponse> => {
  const response = await ragApi.post<RagChatResponse>("/rag/chat", {
    thread_id: threadId,
    client_id: clientId,
    message,
    use_langchain: useLangchain,
  });
  return response.data;
};

export const createThread = async (
  clientId: string,
  title?: string,
): Promise<ChatThread> => {
  const response = await ragApi.post<ChatThread>("/rag/threads", {
    client_id: clientId,
    title,
  });
  return response.data;
};

export const getThreads = async (clientId: string): Promise<ChatThread[]> => {
  const response = await ragApi.get<{ threads: ChatThread[] }>("/rag/threads", {
    params: { client_id: clientId },
  });
  return response.data.threads;
};

export const getThreadMessages = async (
  threadId: string,
): Promise<PersistedChatMessage[]> => {
  const response = await ragApi.get<{ messages: PersistedChatMessage[] }>(
    `/rag/threads/${threadId}/messages`,
  );
  return response.data.messages;
};

export const streamRagMessage = async (
  threadId: string,
  clientId: string,
  message: string,
  useLangchain: boolean,
  callbacks: StreamCallbacks,
): Promise<void> => {
  const response = await fetch(`${AI_AGENT_BASE_URL}/rag/chat/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body: JSON.stringify({
      thread_id: threadId,
      client_id: clientId,
      message,
      use_langchain: useLangchain,
    }),
  });

  if (!response.ok || !response.body) {
    throw new Error("Could not start streaming chat response.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split("\n\n");
    buffer = events.pop() ?? "";

    for (const eventBlock of events) {
      const parsed = parseSseEvent(eventBlock);
      if (!parsed) {
        continue;
      }

      if (parsed.event === "metadata") {
        callbacks.onMetadata(parsed.data as StreamMetadata);
      }
      if (parsed.event === "token") {
        callbacks.onToken(String((parsed.data as { text?: string }).text ?? ""));
      }
      if (parsed.event === "done") {
        callbacks.onDone(String((parsed.data as { answer?: string }).answer ?? ""));
      }
      if (parsed.event === "error") {
        throw new Error(String((parsed.data as { message?: string }).message ?? "Stream failed."));
      }
    }
  }
};

const parseSseEvent = (block: string): { event: string; data: unknown } | null => {
  const eventLine = block
    .split("\n")
    .find((line) => line.startsWith("event:"));
  const dataLine = block
    .split("\n")
    .find((line) => line.startsWith("data:"));

  if (!eventLine || !dataLine) {
    return null;
  }

  return {
    event: eventLine.replace("event:", "").trim(),
    data: JSON.parse(dataLine.replace("data:", "").trim()),
  };
};
