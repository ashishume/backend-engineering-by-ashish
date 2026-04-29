from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class DocumentMetadata(BaseModel):
    document_id: str
    filename: str
    source_type: str
    chunk_count: int
    created_at: datetime


class SourceChunk(BaseModel):
    document_id: str
    filename: str
    chunk_index: int
    text: str
    score: float


class UploadDocumentResponse(BaseModel):
    document: DocumentMetadata


class ListDocumentsResponse(BaseModel):
    documents: list[DocumentMetadata]


class DeleteDocumentResponse(BaseModel):
    document_id: str
    deleted: bool


class CreateThreadRequest(BaseModel):
    client_id: str = Field(..., min_length=1, max_length=128)
    title: str | None = Field(default=None, max_length=160)


class ChatThreadResponse(BaseModel):
    thread_id: str
    client_id: str
    title: str
    created_at: datetime
    updated_at: datetime


class ListThreadsResponse(BaseModel):
    threads: list[ChatThreadResponse]


class ChatMessageResponse(BaseModel):
    id: int
    thread_id: str
    role: Literal["user", "assistant"]
    content: str
    mode: Literal["rag", "general"] | None = None
    created_at: datetime


class ListMessagesResponse(BaseModel):
    messages: list[ChatMessageResponse]


class ThreadMemoryResponse(BaseModel):
    thread_id: str
    summary: str
    facts: dict
    updated_at: datetime


class RagChatRequest(BaseModel):
    session_id: str | None = Field(default=None, min_length=1, max_length=128)
    thread_id: str | None = Field(default=None, min_length=1, max_length=128)
    client_id: str | None = Field(default=None, min_length=1, max_length=128)
    message: str = Field(..., min_length=1)
    top_k: int | None = Field(default=None, ge=1, le=20)
    use_langchain: bool = False


class RagChatResponse(BaseModel):
    answer: str
    mode: Literal["rag", "general"]
    sources: list[SourceChunk] = Field(default_factory=list)
    session_id: str
    thread_id: str
