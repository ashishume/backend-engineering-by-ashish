import axios from "axios";
import type { AgentStep } from "./rag";

const AI_AGENT_BASE_URL = import.meta.env.VITE_AI_AGENT_API_URL || "http://localhost:8001";

const notionAgentApi = axios.create({
  baseURL: AI_AGENT_BASE_URL,
});

export type NotionSourceChunk = {
  page_id: string;
  page_title: string;
  url: string;
  chunk_index: number;
  text: string;
  score: number;
};

export type NotionSourcePage = {
  page_id: string;
  page_title: string;
  url: string;
  chunk_count: number;
  last_edited_time: string | null;
  indexed_at: string;
};

export type NotionSyncResponse = {
  indexed_pages: number;
  indexed_chunks: number;
  skipped_pages: number;
  message: string;
};

export type NotionAgentChatResponse = {
  answer: string;
  mode: "notion_rag";
  sources: NotionSourceChunk[];
  agent_steps: AgentStep[];
  session_id: string;
  thread_id: string;
};

export const syncNotionMemory = async (): Promise<NotionSyncResponse> => {
  const response = await notionAgentApi.post<NotionSyncResponse>("/notion-agent/sync");
  return response.data;
};

export const getNotionSources = async (): Promise<NotionSourcePage[]> => {
  const response = await notionAgentApi.get<{ sources: NotionSourcePage[] }>(
    "/notion-agent/sources",
  );
  return response.data.sources;
};

export const sendNotionAgentMessage = async (
  threadId: string,
  clientId: string,
  message: string,
): Promise<NotionAgentChatResponse> => {
  const response = await notionAgentApi.post<NotionAgentChatResponse>(
    "/notion-agent/chat",
    {
      thread_id: threadId,
      client_id: clientId,
      message,
    },
  );
  return response.data;
};
