from __future__ import annotations

import json
import re
from typing import TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph

from app.core.config import Settings
from app.notion_agent.client import NotionClient
from app.notion_agent.converter import blocks_to_markdown, page_title
from app.notion_agent.vector_store import NotionVectorStore
from app.repositories.thread_repository import ThreadRepository
from app.schemas.notion_agent import (
    NotionAgentChatResponse,
    NotionSourceChunk,
    NotionSourcePage,
    NotionSyncResponse,
)
from app.schemas.rag import AgentStep
from app.services.chunker import TextChunker
from app.services.embeddings import EmbeddingService
from app.services.memory import SessionMemoryService


class NotionSyncState(TypedDict, total=False):
    indexed_pages: int
    indexed_chunks: int
    skipped_pages: int
    message: str


class NotionAgentState(TypedDict, total=False):
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
    sources: list[NotionSourceChunk]
    agent_steps: list[AgentStep]
    draft_answer: str
    answer: str


class NotionAgentService:
    """LangGraph-powered RAG agent over Notion-backed long-term memory."""

    def __init__(
        self,
        *,
        settings: Settings,
        notion_client: NotionClient,
        embeddings: EmbeddingService,
        vector_store: NotionVectorStore,
        chunker: TextChunker,
        memory: SessionMemoryService,
        thread_repository: ThreadRepository,
    ):
        self.settings = settings
        self.notion_client = notion_client
        self.embeddings = embeddings
        self.vector_store = vector_store
        self.chunker = chunker
        self.memory = memory
        self.thread_repository = thread_repository
        self.llm = ChatOpenAI(
            model=settings.chat_model,
            api_key=settings.openrouter_api_key or "missing-openrouter-api-key",
            base_url=settings.openrouter_base_url,
            default_headers={
                "HTTP-Referer": settings.openrouter_http_referer,
                "X-Title": settings.openrouter_app_title,
            },
            temperature=0.2,
        )
        self.sync_graph = self._build_sync_graph()
        self.chat_graph = self._build_chat_graph()

    def sync_notion(self) -> NotionSyncResponse:
        state = self.sync_graph.invoke({})
        return NotionSyncResponse(
            indexed_pages=state.get("indexed_pages", 0),
            indexed_chunks=state.get("indexed_chunks", 0),
            skipped_pages=state.get("skipped_pages", 0),
            message=state.get("message", ""),
        )

    def list_sources(self) -> list[NotionSourcePage]:
        return self.vector_store.list_pages()

    async def chat(
        self,
        *,
        session_id: str | None,
        thread_id: str | None,
        client_id: str | None,
        message: str,
        top_k: int | None,
    ) -> NotionAgentChatResponse:
        state = self.chat_graph.invoke(
            {
                "session_id": session_id,
                "thread_id": thread_id,
                "client_id": client_id,
                "message": message,
                "top_k": top_k,
            }
        )
        return NotionAgentChatResponse(
            answer=state["answer"],
            sources=state.get("sources", []),
            agent_steps=state.get("agent_steps", []),
            session_id=state["active_thread_id"],
            thread_id=state["active_thread_id"],
        )

    def _build_sync_graph(self):
        graph = StateGraph(NotionSyncState)
        graph.add_node("sync_notion", self._sync_notion_node)
        graph.add_edge(START, "sync_notion")
        graph.add_edge("sync_notion", END)
        return graph.compile()

    def _build_chat_graph(self):
        graph = StateGraph(NotionAgentState)
        graph.add_node("prepare_context", self._prepare_context)
        graph.add_node("retriever", self._retrieve)
        graph.add_node("answerer", self._answer)
        graph.add_node("critic", self._critic)
        graph.add_node("save_turn", self._save_turn)

        graph.add_edge(START, "prepare_context")
        graph.add_edge("prepare_context", "retriever")
        graph.add_edge("retriever", "answerer")
        graph.add_edge("answerer", "critic")
        graph.add_edge("critic", "save_turn")
        graph.add_edge("save_turn", END)
        return graph.compile()

    def _sync_notion_node(self, state: NotionSyncState) -> NotionSyncState:
        if not self.notion_client.configured:
            return {
                "indexed_pages": 0,
                "indexed_chunks": 0,
                "skipped_pages": 0,
                "message": "NOTION_API_KEY is not configured; skipped Notion sync.",
            }

        indexed_pages = 0
        indexed_chunks = 0
        skipped_pages = 0
        pages = self.notion_client.search_shared_pages()

        for page in pages:
            page_id = str(page.get("id") or "")
            if (
                not page_id
                or page.get("in_trash")
                or page.get("is_archived")
                or page.get("archived")
            ):
                skipped_pages += 1
                continue

            try:
                blocks = self.notion_client.fetch_block_tree(page_id)
                title = page_title(page)
                body = blocks_to_markdown(blocks)
                if not body:
                    skipped_pages += 1
                    continue

                text = f"# {title}\nURL: {page.get('url') or ''}\n\n{body}"
                chunks = self.chunker.split(text)
                if not chunks:
                    skipped_pages += 1
                    continue

                vectors = self.embeddings.embed_texts(chunks)
                chunk_count = self.vector_store.upsert_page(
                    page_id=page_id,
                    page_title=title,
                    url=str(page.get("url") or ""),
                    last_edited_time=page.get("last_edited_time"),
                    chunks=chunks,
                    vectors=vectors,
                )
                indexed_pages += 1
                indexed_chunks += chunk_count
            except Exception:
                skipped_pages += 1

        return {
            "indexed_pages": indexed_pages,
            "indexed_chunks": indexed_chunks,
            "skipped_pages": skipped_pages,
            "message": (
                f"Indexed {indexed_pages} Notion pages into "
                f"{self.settings.notion_qdrant_collection}."
            ),
        }

    def _prepare_context(self, state: NotionAgentState) -> NotionAgentState:
        thread = self.thread_repository.ensure_thread(
            thread_id=state.get("thread_id") or state.get("session_id"),
            client_id=state.get("client_id"),
        )
        active_thread_id = thread.thread_id
        persisted_messages = self.thread_repository.get_messages(
            active_thread_id,
            limit=self.settings.memory_recent_messages_limit,
        )
        thread_memory = self.thread_repository.get_memory(active_thread_id)

        return {
            "active_thread_id": active_thread_id,
            "bounded_top_k": min(
                state.get("top_k") or self.settings.default_top_k,
                self.settings.max_top_k,
            ),
            "history": self.memory.get_messages_sync(
                active_thread_id, persisted_messages
            ),
            "summary": thread_memory.summary,
            "facts": thread_memory.facts,
            "agent_steps": [],
        }

    def _retrieve(self, state: NotionAgentState) -> NotionAgentState:
        query_vector = self.embeddings.embed_query(state["message"])
        retrieved = self.vector_store.search(query_vector, state["bounded_top_k"])
        sources = [
            source
            for source in retrieved
            if source.score >= self.settings.retrieval_score_threshold
        ]
        return {
            "sources": sources,
            "agent_steps": [
                *state.get("agent_steps", []),
                AgentStep(
                    agent="Retriever",
                    task="Find relevant Notion chunks",
                    output=f"Retrieved {len(sources)} relevant Notion chunks.",
                ),
            ],
        }

    def _answer(self, state: NotionAgentState) -> NotionAgentState:
        sources = state.get("sources", [])
        if not sources:
            draft = (
                "I could not find relevant Notion notes for that question. "
                "Ask me to sync Notion if you recently added the note, or share a "
                "more specific phrase from the page title or content."
            )
        else:
            messages = [
                SystemMessage(
                    content=(
                        "You are the Answerer Agent for a Notion memory RAG system. "
                        "Answer only from the provided Notion context and persistent "
                        "thread memory. Cite Notion facts inline as [Source 1], "
                        "[Source 2], etc. If the context does not support a claim, "
                        "say what is missing."
                    )
                ),
                *self._history_messages(state),
                HumanMessage(
                    content=(
                        f"Persistent memory:\n{self._format_memory(state)}\n\n"
                        f"Question:\n{state['message']}\n\n"
                        f"Notion context:\n{self._format_sources(sources)}"
                    )
                ),
            ]
            draft = self._invoke(messages)

        return {
            "draft_answer": draft,
            "agent_steps": [
                *state.get("agent_steps", []),
                AgentStep(
                    agent="Answerer",
                    task="Draft grounded Notion answer",
                    output=draft,
                ),
            ],
        }

    def _critic(self, state: NotionAgentState) -> NotionAgentState:
        if not state.get("sources"):
            answer = state.get("draft_answer", "")
        else:
            messages = [
                SystemMessage(
                    content=(
                        "You are the Critic Agent for a Notion RAG answer. Return "
                        "only the final user-facing answer. Keep citations that are "
                        "supported by the Notion context. Remove unsupported claims. "
                        "If the answer cannot be supported, say what is missing."
                    )
                ),
                HumanMessage(
                    content=(
                        f"Question:\n{state['message']}\n\n"
                        f"Notion context:\n{self._format_sources(state.get('sources', []))}\n\n"
                        f"Draft answer:\n{state.get('draft_answer', '')}"
                    )
                ),
            ]
            answer = self._invoke(messages)

        return {
            "answer": answer,
            "agent_steps": [
                *state.get("agent_steps", []),
                AgentStep(
                    agent="Critic",
                    task="Verify citations and unsupported claims",
                    output=answer,
                ),
            ],
        }

    def _save_turn(self, state: NotionAgentState) -> NotionAgentState:
        self.thread_repository.add_turn(
            thread_id=state["active_thread_id"],
            user_message=state["message"],
            assistant_message=state["answer"],
            mode="notion_rag",
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

    def _history_messages(self, state: NotionAgentState) -> list[BaseMessage]:
        messages: list[BaseMessage] = []
        for message in state.get("history", [])[-8:]:
            content = message.get("content", "")
            if message.get("role") == "assistant":
                messages.append(AIMessage(content=content))
            elif message.get("role") == "user":
                messages.append(HumanMessage(content=content))
        return messages

    def _format_sources(self, sources: list[NotionSourceChunk]) -> str:
        return "\n\n".join(
            f"[Source {index + 1}: {source.page_title}, chunk {source.chunk_index}, "
            f"score {source.score:.2f}, url {source.url}]\n{source.text}"
            for index, source in enumerate(sources)
        )

    def _format_memory(self, state: NotionAgentState) -> str:
        facts = state.get("facts", {})
        facts_text = json.dumps(facts, ensure_ascii=False) if facts else "{}"
        return (
            f"Summary: {state.get('summary') or 'No prior summary.'}\n"
            f"Stable facts: {facts_text}"
        )

    def _invoke(self, messages: list[BaseMessage]) -> str:
        result = self.llm.invoke(messages)
        content = result.content
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    parts.append(str(item.get("text") or item.get("content") or ""))
                else:
                    parts.append(str(item))
            return "".join(parts).strip()
        return str(content or "").strip()

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
        for pattern in (
            r"\bmy name is\s+([A-Z][A-Za-z0-9_-]{1,40})",
            r"\bi am\s+([A-Z][A-Za-z0-9_-]{1,40})",
            r"\bi'm\s+([A-Z][A-Za-z0-9_-]{1,40})",
        ):
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
            f"User: {user_message.strip()}\n" f"Assistant: {assistant_message.strip()}"
        )
        combined = f"{previous_summary.strip()}\n\n{exchange}".strip()
        return combined[-2500:]
