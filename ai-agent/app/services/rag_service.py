from __future__ import annotations

import json
import re
from uuid import uuid4

from fastapi import UploadFile
from openai import OpenAI

from app.core.config import Settings
from app.repositories.thread_repository import ThreadRepository
from app.schemas.rag import (
    ChatMessageResponse,
    ChatThreadResponse,
    DocumentMetadata,
    RagChatResponse,
    SourceChunk,
)
from app.services.chunker import TextChunker
from app.services.document_loader import DocumentLoader
from app.services.embeddings import EmbeddingService
from app.services.memory import SessionMemoryService
from app.services.vector_store import QdrantVectorStore


class RagService:
    """Coordinates document indexing, retrieval, memory, and answer generation."""

    def __init__(
        self,
        *,
        settings: Settings,
        llm_client: OpenAI,
        loader: DocumentLoader,
        chunker: TextChunker,
        embeddings: EmbeddingService,
        vector_store: QdrantVectorStore,
        memory: SessionMemoryService,
        thread_repository: ThreadRepository,
    ):
        self.settings = settings
        self.llm_client = llm_client
        self.loader = loader
        self.chunker = chunker
        self.embeddings = embeddings
        self.vector_store = vector_store
        self.memory = memory
        self.thread_repository = thread_repository

    async def index_document(self, upload: UploadFile) -> DocumentMetadata:
        """Parse, chunk, embed, and persist one uploaded document."""

        text, source_type = await self.loader.load(upload, self.settings.max_upload_mb)
        chunks = self.chunker.split(text)
        if not chunks:
            raise ValueError("Document could not be split into searchable chunks")

        vectors = self.embeddings.embed_texts(chunks)
        return self.vector_store.upsert_document(
            document_id=str(uuid4()),
            filename=upload.filename or "document",
            source_type=source_type,
            chunks=chunks,
            vectors=vectors,
        )

    def list_documents(self) -> list[DocumentMetadata]:
        """Return document metadata reconstructed from Qdrant payloads."""

        return self.vector_store.list_documents()

    def delete_document(self, document_id: str) -> bool:
        """Remove a document and all of its indexed chunks."""

        return self.vector_store.delete_document(document_id)

    def create_thread(self, *, client_id: str, title: str | None = None) -> ChatThreadResponse:
        """Create a persistent chat thread for an anonymous browser client."""

        return self.thread_repository.create_thread(client_id=client_id, title=title)

    def list_threads(self, *, client_id: str) -> list[ChatThreadResponse]:
        """List persistent threads for one anonymous browser client."""

        return self.thread_repository.list_threads(client_id)

    def get_thread_messages(self, *, thread_id: str) -> list[ChatMessageResponse]:
        """Return persisted visible chat messages for a thread."""

        return self.thread_repository.get_messages(thread_id)

    async def chat(
        self,
        *,
        session_id: str | None,
        thread_id: str | None,
        client_id: str | None,
        message: str,
        top_k: int | None,
    ) -> RagChatResponse:
        """Answer a user message with RAG grounding when retrieval is relevant.

        Retrieval context and chat memory are intentionally assembled separately:
        retrieved chunks ground facts from documents, while session memory keeps
        the conversation coherent across follow-up questions.
        """

        thread = self._ensure_thread(thread_id=thread_id, session_id=session_id, client_id=client_id)
        active_thread_id = thread.thread_id
        bounded_top_k = min(top_k or self.settings.default_top_k, self.settings.max_top_k)
        query_vector = self.embeddings.embed_query(message)
        retrieved = self.vector_store.search(query_vector, bounded_top_k)
        relevant_sources = [
            source
            for source in retrieved
            if source.score >= self.settings.retrieval_score_threshold
        ]

        mode = "rag" if relevant_sources else "general"
        persisted_messages = self.thread_repository.get_messages(
            active_thread_id,
            limit=self.settings.memory_recent_messages_limit,
        )
        thread_memory = self.thread_repository.get_memory(active_thread_id)
        history = self.memory.get_messages_sync(active_thread_id, persisted_messages)
        messages = self._build_messages(
            history=history,
            user_message=message,
            sources=relevant_sources,
            use_rag=mode == "rag",
            summary=thread_memory.summary,
            facts=thread_memory.facts,
        )
        answer = self._complete(messages)
        self.thread_repository.add_turn(
            thread_id=active_thread_id,
            user_message=message,
            assistant_message=answer,
            mode=mode,
        )
        await self.memory.add_turn(active_thread_id, message, answer)
        self._update_thread_memory(
            thread_id=active_thread_id,
            previous_summary=thread_memory.summary,
            previous_facts=thread_memory.facts,
            user_message=message,
            assistant_message=answer,
        )

        return RagChatResponse(
            answer=answer,
            mode=mode,
            sources=relevant_sources if mode == "rag" else [],
            session_id=active_thread_id,
            thread_id=active_thread_id,
        )

    def _build_messages(
        self,
        *,
        history: list[dict[str, str]],
        user_message: str,
        sources: list[SourceChunk],
        use_rag: bool,
        summary: str = "",
        facts: dict | None = None,
    ) -> list[dict[str, str]]:
        """Build the final prompt payload sent to OpenRouter."""

        memory_context = self._format_memory_context(summary=summary, facts=facts or {})
        if use_rag:
            context = "\n\n".join(
                f"[Source {index + 1}: {source.filename}, chunk {source.chunk_index}]\n{source.text}"
                for index, source in enumerate(sources)
            )
            system = (
                "You are a helpful RAG assistant. Use the provided document context "
                "when it answers the user. Cite sources inline as [Source 1], "
                "[Source 2], etc. If the context is insufficient, say what is missing "
                "and answer generally only when that is clearly helpful.\n\n"
                f"{memory_context}\n\n"
                f"Document context:\n{context}"
            )
        else:
            system = (
                "You are a helpful assistant. The user's latest question did not match "
                "the uploaded document context strongly enough, so answer generally. "
                "Do not claim that the answer came from uploaded documents.\n\n"
                f"{memory_context}"
            )

        return [
            {"role": "system", "content": system},
            *history[-12:],
            {"role": "user", "content": user_message},
        ]

    def _complete(self, messages: list[dict[str, str]]) -> str:
        """Call OpenRouter chat completions and return the assistant text."""

        response = self.llm_client.chat.completions.create(
            model=self.settings.chat_model,
            messages=messages,
            temperature=0.2,
        )
        return response.choices[0].message.content or ""

    def stream_chat(
        self,
        *,
        session_id: str | None,
        thread_id: str | None,
        client_id: str | None,
        message: str,
        top_k: int | None,
    ):
        """Yield Server-Sent Events for a streaming chat answer.

        The final assistant text is accumulated while tokens stream to the
        client, then stored in LlamaIndex memory once the model finishes.
        """

        try:
            thread = self._ensure_thread(
                thread_id=thread_id,
                session_id=session_id,
                client_id=client_id,
            )
            active_thread_id = thread.thread_id
            bounded_top_k = min(
                top_k or self.settings.default_top_k, self.settings.max_top_k
            )
            query_vector = self.embeddings.embed_query(message)
            retrieved = self.vector_store.search(query_vector, bounded_top_k)
            relevant_sources = [
                source
                for source in retrieved
                if source.score >= self.settings.retrieval_score_threshold
            ]
            mode = "rag" if relevant_sources else "general"
            sources = relevant_sources if mode == "rag" else []
            persisted_messages = self.thread_repository.get_messages(
                active_thread_id,
                limit=self.settings.memory_recent_messages_limit,
            )
            thread_memory = self.thread_repository.get_memory(active_thread_id)
            history = self.memory.get_messages_sync(active_thread_id, persisted_messages)
            messages = self._build_messages(
                history=history,
                user_message=message,
                sources=sources,
                use_rag=mode == "rag",
                summary=thread_memory.summary,
                facts=thread_memory.facts,
            )

            yield self._sse(
                "metadata",
                {
                    "mode": mode,
                    "sources": [source.model_dump() for source in sources],
                    "session_id": active_thread_id,
                    "thread_id": active_thread_id,
                },
            )

            answer_parts: list[str] = []
            stream = self.llm_client.chat.completions.create(
                model=self.settings.chat_model,
                messages=messages,
                temperature=0.2,
                stream=True,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta.content or ""
                if not delta:
                    continue
                answer_parts.append(delta)
                yield self._sse("token", {"text": delta})

            answer = "".join(answer_parts)
            self.thread_repository.add_turn(
                thread_id=active_thread_id,
                user_message=message,
                assistant_message=answer,
                mode=mode,
            )
            self.memory.add_turn_sync(active_thread_id, message, answer)
            self._update_thread_memory(
                thread_id=active_thread_id,
                previous_summary=thread_memory.summary,
                previous_facts=thread_memory.facts,
                user_message=message,
                assistant_message=answer,
            )
            yield self._sse("done", {"answer": answer})
        except Exception as exc:
            yield self._sse("error", {"message": str(exc)})

    def _sse(self, event: str, data: dict) -> str:
        """Serialize one Server-Sent Event frame."""

        return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"

    def _ensure_thread(
        self, *, thread_id: str | None, session_id: str | None, client_id: str | None
    ) -> ChatThreadResponse:
        """Resolve the active thread, using session_id as a legacy thread alias."""

        return self.thread_repository.ensure_thread(
            thread_id=thread_id or session_id,
            client_id=client_id,
        )

    def _format_memory_context(self, *, summary: str, facts: dict) -> str:
        """Format persisted thread memory as a compact system-prompt block."""

        facts_text = json.dumps(facts, ensure_ascii=False) if facts else "{}"
        return (
            "Persistent thread memory:\n"
            f"- Summary: {summary or 'No prior summary.'}\n"
            f"- Stable facts: {facts_text}\n"
            "Use this memory only for this thread. If the user asks for a remembered "
            "fact such as their name, answer from these stable facts when available."
        )

    def _update_thread_memory(
        self,
        *,
        thread_id: str,
        previous_summary: str,
        previous_facts: dict,
        user_message: str,
        assistant_message: str,
    ) -> None:
        """Update durable thread memory after a completed assistant response."""

        facts = dict(previous_facts or {})
        facts.update(self._extract_stable_facts(user_message))
        summary = self._summarize_locally(
            previous_summary=previous_summary,
            user_message=user_message,
            assistant_message=assistant_message,
        )
        self.thread_repository.update_memory(
            thread_id=thread_id,
            summary=summary,
            facts=facts,
        )

    def _extract_stable_facts(self, user_message: str) -> dict:
        """Extract obvious stable facts without spending an extra model call."""

        facts: dict[str, str] = {}
        name_patterns = [
            r"\bmy name is\s+([A-Z][A-Za-z0-9_-]{1,40})",
            r"\bi am\s+([A-Z][A-Za-z0-9_-]{1,40})",
            r"\bi'm\s+([A-Z][A-Za-z0-9_-]{1,40})",
        ]
        for pattern in name_patterns:
            match = re.search(pattern, user_message, flags=re.IGNORECASE)
            if match:
                name = match.group(1).strip(" .,!?:;")
                facts["name"] = name[:1].upper() + name[1:]
                break
        return facts

    def _summarize_locally(
        self, *, previous_summary: str, user_message: str, assistant_message: str
    ) -> str:
        """Maintain a small rolling summary for pgAdmin-visible thread context."""

        exchange = (
            f"User: {user_message.strip()}\n"
            f"Assistant: {assistant_message.strip()}"
        )
        combined = f"{previous_summary.strip()}\n\n{exchange}".strip()
        return combined[-2500:]
