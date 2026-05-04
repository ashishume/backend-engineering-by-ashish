from __future__ import annotations

import json
import re
from typing import Literal, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph

from app.core.config import Settings
from app.repositories.thread_repository import ThreadRepository
from app.schemas.rag import AgentStep, MultiAgentChatResponse, SourceChunk
from app.services.embeddings import EmbeddingService
from app.services.memory import SessionMemoryService
from app.services.vector_store import QdrantVectorStore


class CustomerAgentState(TypedDict, total=False):
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
    agent_steps: list[AgentStep]
    triage: str
    knowledge: str
    resolution: str
    answer: str


class MultiAgentCustomerService:
    """Customer-support workflow where each LangGraph node owns one agent task."""

    def __init__(
        self,
        *,
        settings: Settings,
        embeddings: EmbeddingService,
        vector_store: QdrantVectorStore,
        memory: SessionMemoryService,
        thread_repository: ThreadRepository,
    ):
        self.settings = settings
        self.embeddings = embeddings
        self.vector_store = vector_store
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
        self.graph = self._build_graph()

    async def chat(
        self,
        *,
        session_id: str | None,
        thread_id: str | None,
        client_id: str | None,
        message: str,
        top_k: int | None,
    ) -> MultiAgentChatResponse:
        state = self.graph.invoke(
            {
                "session_id": session_id,
                "thread_id": thread_id,
                "client_id": client_id,
                "message": message,
                "top_k": top_k,
            }
        )
        return MultiAgentChatResponse(
            answer=state["answer"],
            sources=state.get("sources", []),
            agent_steps=state.get("agent_steps", []),
            session_id=state["active_thread_id"],
            thread_id=state["active_thread_id"],
        )

    def _build_graph(self):
        graph = StateGraph(CustomerAgentState)
        graph.add_node("prepare_context", self._prepare_context)
        graph.add_node("intake_agent", self._run_intake_agent)
        graph.add_node("knowledge_agent", self._run_knowledge_agent)
        graph.add_node("resolution_agent", self._run_resolution_agent)
        graph.add_node("quality_agent", self._run_quality_agent)
        graph.add_node("save_turn", self._save_turn)

        graph.add_edge(START, "prepare_context")
        graph.add_edge("prepare_context", "intake_agent")
        graph.add_edge("intake_agent", "knowledge_agent")
        graph.add_edge("knowledge_agent", "resolution_agent")
        graph.add_edge("resolution_agent", "quality_agent")
        graph.add_edge("quality_agent", "save_turn")
        graph.add_edge("save_turn", END)
        return graph.compile()

    def _prepare_context(self, state: CustomerAgentState) -> CustomerAgentState:
        thread = self.thread_repository.ensure_thread(
            thread_id=state.get("thread_id") or state.get("session_id"),
            client_id=state.get("client_id"),
        )
        active_thread_id = thread.thread_id
        bounded_top_k = min(
            state.get("top_k") or self.settings.default_top_k,
            self.settings.max_top_k,
        )
        persisted_messages = self.thread_repository.get_messages(
            active_thread_id,
            limit=self.settings.memory_recent_messages_limit,
        )
        thread_memory = self.thread_repository.get_memory(active_thread_id)
        sources = self._retrieve_sources(state["message"], bounded_top_k)

        return {
            "active_thread_id": active_thread_id,
            "bounded_top_k": bounded_top_k,
            "history": self.memory.get_messages_sync(active_thread_id, persisted_messages),
            "summary": thread_memory.summary,
            "facts": thread_memory.facts,
            "sources": sources,
            "agent_steps": [],
        }

    def _run_intake_agent(self, state: CustomerAgentState) -> CustomerAgentState:
        prompt = [
            SystemMessage(
                content=(
                    "You are the Intake Agent in a customer-support team. "
                    "Classify the customer's intent, urgency, sentiment, and any "
                    "missing information. Return concise operational notes only."
                )
            ),
            *self._history_messages(state),
            HumanMessage(content=state["message"]),
        ]
        triage = self._invoke(prompt)
        return {
            "triage": triage,
            "agent_steps": [
                *state.get("agent_steps", []),
                AgentStep(agent="Intake Agent", task="Classify intent and urgency", output=triage),
            ],
        }

    def _run_knowledge_agent(self, state: CustomerAgentState) -> CustomerAgentState:
        source_context = self._format_sources(state.get("sources", []))
        prompt = [
            SystemMessage(
                content=(
                    "You are the Knowledge Agent. Use uploaded document chunks when "
                    "they are relevant. Distinguish documented facts from reasonable "
                    "general support guidance. Cite document facts as [Source 1], "
                    "[Source 2], etc. If no source supports the answer, say so."
                )
            ),
            HumanMessage(
                content=(
                    f"Customer request:\n{state['message']}\n\n"
                    f"Intake notes:\n{state.get('triage', '')}\n\n"
                    f"Document context:\n{source_context or 'No relevant document chunks found.'}"
                )
            ),
        ]
        knowledge = self._invoke(prompt)
        return {
            "knowledge": knowledge,
            "agent_steps": [
                *state.get("agent_steps", []),
                AgentStep(
                    agent="Knowledge Agent",
                    task="Retrieve and interpret uploaded-document context",
                    output=knowledge,
                ),
            ],
        }

    def _run_resolution_agent(self, state: CustomerAgentState) -> CustomerAgentState:
        prompt = [
            SystemMessage(
                content=(
                    "You are the Resolution Agent. Draft a customer-facing answer "
                    "that is empathetic, direct, and action-oriented. If required "
                    "details are missing, ask for the smallest useful set of details. "
                    "Do not invent policies, order statuses, refunds, or account facts."
                )
            ),
            HumanMessage(
                content=(
                    f"Customer request:\n{state['message']}\n\n"
                    f"Persistent memory:\n{self._format_memory(state)}\n\n"
                    f"Intake notes:\n{state.get('triage', '')}\n\n"
                    f"Knowledge notes:\n{state.get('knowledge', '')}"
                )
            ),
        ]
        resolution = self._invoke(prompt)
        return {
            "resolution": resolution,
            "agent_steps": [
                *state.get("agent_steps", []),
                AgentStep(
                    agent="Resolution Agent",
                    task="Draft customer-facing response",
                    output=resolution,
                ),
            ],
        }

    def _run_quality_agent(self, state: CustomerAgentState) -> CustomerAgentState:
        prompt = [
            SystemMessage(
                content=(
                    "You are the Quality Agent. Review the draft for accuracy, "
                    "support usefulness, source discipline, and tone. Return only "
                    "the final customer-facing answer. Keep document citations that "
                    "are already supported by the Knowledge Agent."
                )
            ),
            HumanMessage(
                content=(
                    f"Customer request:\n{state['message']}\n\n"
                    f"Intake notes:\n{state.get('triage', '')}\n\n"
                    f"Knowledge notes:\n{state.get('knowledge', '')}\n\n"
                    f"Draft answer:\n{state.get('resolution', '')}"
                )
            ),
        ]
        answer = self._invoke(prompt)
        return {
            "answer": answer,
            "agent_steps": [
                *state.get("agent_steps", []),
                AgentStep(
                    agent="Quality Agent",
                    task="Check accuracy and finalize answer",
                    output=answer,
                ),
            ],
        }

    def _save_turn(self, state: CustomerAgentState) -> CustomerAgentState:
        self.thread_repository.add_turn(
            thread_id=state["active_thread_id"],
            user_message=state["message"],
            assistant_message=state["answer"],
            mode="multi_agent",
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

    def _retrieve_sources(self, message: str, top_k: int) -> list[SourceChunk]:
        query_vector = self.embeddings.embed_query(message)
        retrieved = self.vector_store.search(query_vector, top_k)
        return [
            source
            for source in retrieved
            if source.score >= self.settings.retrieval_score_threshold
        ]

    def _history_messages(self, state: CustomerAgentState) -> list[BaseMessage]:
        messages: list[BaseMessage] = []
        for message in state.get("history", [])[-8:]:
            content = message.get("content", "")
            if message.get("role") == "assistant":
                messages.append(AIMessage(content=content))
            elif message.get("role") == "user":
                messages.append(HumanMessage(content=content))
        return messages

    def _format_sources(self, sources: list[SourceChunk]) -> str:
        return "\n\n".join(
            f"[Source {index + 1}: {source.filename}, chunk {source.chunk_index}, "
            f"score {source.score:.2f}]\n{source.text}"
            for index, source in enumerate(sources)
        )

    def _format_memory(self, state: CustomerAgentState) -> str:
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
            f"User: {user_message.strip()}\n"
            f"Assistant: {assistant_message.strip()}"
        )
        combined = f"{previous_summary.strip()}\n\n{exchange}".strip()
        return combined[-2500:]
