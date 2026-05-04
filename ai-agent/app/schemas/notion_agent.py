from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.rag import AgentStep


class NotionSourceChunk(BaseModel):
    page_id: str
    page_title: str
    url: str
    chunk_index: int
    text: str
    score: float


class NotionSourcePage(BaseModel):
    page_id: str
    page_title: str
    url: str
    chunk_count: int
    last_edited_time: datetime | None = None
    indexed_at: datetime


class NotionSyncResponse(BaseModel):
    indexed_pages: int
    indexed_chunks: int
    skipped_pages: int
    message: str


class ListNotionSourcesResponse(BaseModel):
    sources: list[NotionSourcePage]


class NotionAgentChatRequest(BaseModel):
    session_id: str | None = Field(default=None, min_length=1, max_length=128)
    thread_id: str | None = Field(default=None, min_length=1, max_length=128)
    client_id: str | None = Field(default=None, min_length=1, max_length=128)
    message: str = Field(..., min_length=1)
    top_k: int | None = Field(default=None, ge=1, le=20)


class NotionAgentChatResponse(BaseModel):
    answer: str
    mode: Literal["notion_rag"] = "notion_rag"
    sources: list[NotionSourceChunk] = Field(default_factory=list)
    agent_steps: list[AgentStep] = Field(default_factory=list)
    session_id: str
    thread_id: str
