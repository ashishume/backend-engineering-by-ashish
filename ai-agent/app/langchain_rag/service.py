from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Literal, TypedDict
from uuid import uuid4

from fastapi import UploadFile
from langchain_core.documents import Document
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore, RetrievalMode
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langgraph.graph import END, START, StateGraph
from qdrant_client import QdrantClient

from app.core.config import Settings
from app.repositories.thread_repository import ThreadRepository
from app.schemas.rag import (
    ChatMessageResponse,
    ChatThreadResponse,
    DocumentMetadata,
    RagChatResponse,
    SourceChunk,
)
from app.services.document_loader import DocumentLoader
from app.services.memory import SessionMemoryService
from app.services.vector_store import QdrantVectorStore as ManualQdrantVectorStore


class RagGraphState(TypedDict, total=False):
    session_id: str | None
    thread_id: str | None
    client_id: str | None
    message: str
    top_k: int | None
    active_thread_id: str
    bounded_top_k: int
    history: list[dict[str, str]]
    summary: str
    facts: dict
    sources: list[SourceChunk]
    mode: Literal["rag", "general"]
    answer: str


class LangChainGraphRagService:
    """Same RAG behavior as RagService, built with LangChain and LangGraph.

    This class intentionally lives next to, not instead of, the manual service.
    It lets you compare how the same app behavior looks with library-provided
    splitters, embeddings, vector-store wrappers, prompt templates, LLM wrappers,
    and a graph-based workflow.
    """

    def __init__(
        self,
        *,
        settings: Settings,
        qdrant_client: QdrantClient,
        loader: DocumentLoader,
        manual_vector_store: ManualQdrantVectorStore,
        memory: SessionMemoryService,
        thread_repository: ThreadRepository,
    ):
        self.settings = settings
        self.qdrant_client = qdrant_client
        self.loader = loader
        self.manual_vector_store = manual_vector_store
        self.memory = memory
        self.thread_repository = thread_repository
        self.splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            encoding_name="cl100k_base",
            chunk_size=settings.chunk_token_size,
            chunk_overlap=settings.chunk_token_overlap,
        )
        self.embeddings = OpenAIEmbeddings(
            model=settings.embedding_model,
            api_key=settings.openrouter_api_key or "missing-openrouter-api-key",
            base_url=settings.openrouter_base_url,
            default_headers=self._openrouter_headers(),
            chunk_size=settings.embedding_batch_size,
            check_embedding_ctx_length=False,
            tiktoken_model_name="text-embedding-3-small",
        )
        self.llm = ChatOpenAI(
            model=settings.chat_model,
            api_key=settings.openrouter_api_key or "missing-openrouter-api-key",
            base_url=settings.openrouter_base_url,
            default_headers=self._openrouter_headers(),
            temperature=0.2,
        )
        self.rag_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    (
                        "You are a helpful RAG assistant. Use the provided document "
                        "context when it answers the user. Cite sources inline as "
                        "[Source 1], [Source 2], etc. If the context is insufficient, "
                        "say what is missing and answer generally only when that is "
                        "clearly helpful.\n\n{memory_context}\n\n"
                        "Document context:\n{document_context}"
                    ),
                ),
                MessagesPlaceholder("history"),
                ("human", "{question}"),
            ]
        )
        self.general_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    (
                        "You are a helpful assistant. The user's latest question did "
                        "not match the uploaded document context strongly enough, so "
                        "answer generally. Do not claim that the answer came from "
                        "uploaded documents.\n\n{memory_context}"
                    ),
                ),
                MessagesPlaceholder("history"),
                ("human", "{question}"),
            ]
        )
        self.graph = self._build_graph()

    async def index_document(self, upload: UploadFile) -> DocumentMetadata:
        """Parse, split, embed, and store one document using LangChain pieces."""

        text, source_type = await self.loader.load(upload, self.settings.max_upload_mb)
        chunks = self.splitter.split_text(text)
        if not chunks:
            raise ValueError("Document could not be split into searchable chunks")

        document_id = str(uuid4())
        filename = upload.filename or "document"
        created_at = datetime.now(timezone.utc)
        documents = [
            Document(
                page_content=chunk,
                metadata={
                    "document_id": document_id,
                    "filename": filename,
                    "source_type": source_type,
                    "chunk_index": index,
                    "created_at": created_at.isoformat(),
                },
            )
            for index, chunk in enumerate(chunks)
        ]
        ids = [str(uuid4()) for _ in documents]
        vector_store = QdrantVectorStore.from_documents(
            documents=documents,
            embedding=self.embeddings,
            ids=ids,
            collection_name=self.settings.qdrant_collection,
            url=self.settings.qdrant_url,
            api_key=self.settings.qdrant_api_key,
            content_payload_key="text",
            metadata_payload_key="metadata",
            vector_name="",
            retrieval_mode=RetrievalMode.DENSE,
            force_recreate=False,
        )
        # Keep the same client instance warm for later reads.
        vector_store.client.close()

        return DocumentMetadata(
            document_id=document_id,
            filename=filename,
            source_type=source_type,
            chunk_count=len(chunks),
            created_at=created_at,
        )

    def list_documents(self) -> list[DocumentMetadata]:
        """Document-management behavior stays custom to your product."""

        return self.manual_vector_store.list_documents()

    def delete_document(self, document_id: str) -> bool:
        """Deletion by your product document id stays custom."""

        return self.manual_vector_store.delete_document(document_id)

    def create_thread(self, *, client_id: str, title: str | None = None) -> ChatThreadResponse:
        return self.thread_repository.create_thread(client_id=client_id, title=title)

    def list_threads(self, *, client_id: str) -> list[ChatThreadResponse]:
        return self.thread_repository.list_threads(client_id)

    def get_thread_messages(self, *, thread_id: str) -> list[ChatMessageResponse]:
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
        """Run chat through a LangGraph workflow."""

        state = self.graph.invoke(
            {
                "session_id": session_id,
                "thread_id": thread_id,
                "client_id": client_id,
                "message": message,
                "top_k": top_k,
            }
        )
        return RagChatResponse(
            answer=state["answer"],
            mode=state["mode"],
            sources=state["sources"] if state["mode"] == "rag" else [],
            session_id=state["active_thread_id"],
            thread_id=state["active_thread_id"],
        )

    def stream_chat(
        self,
        *,
        session_id: str | None,
        thread_id: str | None,
        client_id: str | None,
        message: str,
        top_k: int | None,
    ):
        """Stream a LangChain-generated answer while reusing graph preparation."""

        try:
            state: RagGraphState = {
                "session_id": session_id,
                "thread_id": thread_id,
                "client_id": client_id,
                "message": message,
                "top_k": top_k,
            }
            for node in (
                self._ensure_thread,
                self._load_memory,
                self._retrieve_sources,
                self._decide_mode,
            ):
                state.update(node(state))

            sources = state["sources"] if state["mode"] == "rag" else []
            yield self._sse(
                "metadata",
                {
                    "mode": state["mode"],
                    "sources": [source.model_dump() for source in sources],
                    "session_id": state["active_thread_id"],
                    "thread_id": state["active_thread_id"],
                },
            )

            answer_parts: list[str] = []
            prompt_value = self._prompt_value(state)
            for chunk in self.llm.stream(prompt_value):
                text = self._message_content_to_text(chunk.content)
                if not text:
                    continue
                answer_parts.append(text)
                yield self._sse("token", {"text": text})

            answer = "".join(answer_parts)
            state["answer"] = answer
            self._save_turn(state)
            yield self._sse("done", {"answer": answer})
        except Exception as exc:
            yield self._sse("error", {"message": str(exc)})

    def _build_graph(self):
        graph = StateGraph(RagGraphState)
        graph.add_node("ensure_thread", self._ensure_thread)
        graph.add_node("load_memory", self._load_memory)
        graph.add_node("retrieve_sources", self._retrieve_sources)
        graph.add_node("decide_mode", self._decide_mode)
        graph.add_node("generate_answer", self._generate_answer)
        graph.add_node("save_turn", self._save_turn)

        graph.add_edge(START, "ensure_thread")
        graph.add_edge("ensure_thread", "load_memory")
        graph.add_edge("load_memory", "retrieve_sources")
        graph.add_edge("retrieve_sources", "decide_mode")
        graph.add_edge("decide_mode", "generate_answer")
        graph.add_edge("generate_answer", "save_turn")
        graph.add_edge("save_turn", END)
        return graph.compile()

    def _ensure_thread(self, state: RagGraphState) -> RagGraphState:
        thread = self.thread_repository.ensure_thread(
            thread_id=state.get("thread_id") or state.get("session_id"),
            client_id=state.get("client_id"),
        )
        return {
            "active_thread_id": thread.thread_id,
            "bounded_top_k": min(
                state.get("top_k") or self.settings.default_top_k,
                self.settings.max_top_k,
            ),
        }

    def _load_memory(self, state: RagGraphState) -> RagGraphState:
        active_thread_id = state["active_thread_id"]
        persisted_messages = self.thread_repository.get_messages(
            active_thread_id,
            limit=self.settings.memory_recent_messages_limit,
        )
        thread_memory = self.thread_repository.get_memory(active_thread_id)
        return {
            "history": self.memory.get_messages_sync(active_thread_id, persisted_messages),
            "summary": thread_memory.summary,
            "facts": thread_memory.facts,
        }

    def _retrieve_sources(self, state: RagGraphState) -> RagGraphState:
        vector_store = self._vector_store()
        try:
            docs_with_scores = vector_store.similarity_search_with_score(
                state["message"],
                k=state["bounded_top_k"],
            )
        except Exception as exc:
            if "Not found" in str(exc) or "doesn't exist" in str(exc):
                docs_with_scores = []
            else:
                raise

        sources = [
            self._source_from_document(document, score)
            for document, score in docs_with_scores
            if score >= self.settings.retrieval_score_threshold
        ]
        return {"sources": sources}

    def _decide_mode(self, state: RagGraphState) -> RagGraphState:
        return {"mode": "rag" if state.get("sources") else "general"}

    def _generate_answer(self, state: RagGraphState) -> RagGraphState:
        result = self.llm.invoke(self._prompt_value(state))
        return {"answer": self._message_content_to_text(result.content)}

    def _save_turn(self, state: RagGraphState) -> RagGraphState:
        self.thread_repository.add_turn(
            thread_id=state["active_thread_id"],
            user_message=state["message"],
            assistant_message=state["answer"],
            mode=state["mode"],
        )
        self.memory.add_turn_sync(
            state["active_thread_id"],
            state["message"],
            state["answer"],
        )
        self._update_thread_memory(
            thread_id=state["active_thread_id"],
            previous_summary=state.get("summary", ""),
            previous_facts=state.get("facts", {}),
            user_message=state["message"],
            assistant_message=state["answer"],
        )
        return {}

    def _vector_store(self) -> QdrantVectorStore:
        return QdrantVectorStore(
            client=self.qdrant_client,
            collection_name=self.settings.qdrant_collection,
            embedding=self.embeddings,
            retrieval_mode=RetrievalMode.DENSE,
            vector_name="",
            content_payload_key="text",
            metadata_payload_key="metadata",
            validate_collection_config=False,
        )

    def _prompt_value(self, state: RagGraphState):
        memory_context = self._format_memory_context(
            summary=state.get("summary", ""),
            facts=state.get("facts", {}),
        )
        history = self._to_langchain_history(state.get("history", []))
        if state["mode"] == "rag":
            document_context = "\n\n".join(
                f"[Source {index + 1}: {source.filename}, chunk {source.chunk_index}]\n"
                f"{source.text}"
                for index, source in enumerate(state.get("sources", []))
            )
            return self.rag_prompt.invoke(
                {
                    "memory_context": memory_context,
                    "document_context": document_context,
                    "history": history[-12:],
                    "question": state["message"],
                }
            )

        return self.general_prompt.invoke(
            {
                "memory_context": memory_context,
                "history": history[-12:],
                "question": state["message"],
            }
        )

    def _source_from_document(self, document: Document, score: float) -> SourceChunk:
        metadata = document.metadata or {}
        return SourceChunk(
            document_id=str(metadata.get("document_id", "")),
            filename=str(metadata.get("filename", "")),
            chunk_index=int(metadata.get("chunk_index", 0)),
            text=document.page_content,
            score=float(score or 0.0),
        )

    def _to_langchain_history(self, history: list[dict[str, str]]) -> list[BaseMessage]:
        messages: list[BaseMessage] = []
        for message in history:
            role = message.get("role")
            content = message.get("content", "")
            if role == "assistant":
                messages.append(AIMessage(content=content))
            elif role == "user":
                messages.append(HumanMessage(content=content))
        return messages

    def _format_memory_context(self, *, summary: str, facts: dict) -> str:
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
        exchange = (
            f"User: {user_message.strip()}\n"
            f"Assistant: {assistant_message.strip()}"
        )
        combined = f"{previous_summary.strip()}\n\n{exchange}".strip()
        return combined[-2500:]

    def _message_content_to_text(self, content) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    parts.append(str(item.get("text") or item.get("content") or ""))
                else:
                    parts.append(str(item))
            return "".join(parts)
        return str(content or "")

    def _openrouter_headers(self) -> dict[str, str]:
        return {
            "HTTP-Referer": self.settings.openrouter_http_referer,
            "X-Title": self.settings.openrouter_app_title,
        }

    def _sse(self, event: str, data: dict) -> str:
        return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"
