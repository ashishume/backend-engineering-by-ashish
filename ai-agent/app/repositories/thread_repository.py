from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ChatMessage, ChatThread, ThreadMemory
from app.schemas.rag import ChatMessageResponse, ChatThreadResponse, ThreadMemoryResponse


class ThreadRepository:
    """Persistence layer for anonymous chat threads and their memory state."""

    def __init__(self, session_factory):
        self.session_factory = session_factory

    def create_thread(
        self, client_id: str, title: str | None = None, thread_id: str | None = None
    ) -> ChatThreadResponse:
        """Create a new anonymous thread and its matching memory row."""

        with self.session_factory() as db:
            thread = ChatThread(
                id=thread_id or str(uuid4()),
                client_id=client_id,
                title=title or "New chat",
            )
            db.add(thread)
            db.add(ThreadMemory(thread_id=thread.id, summary="", facts={}))
            db.commit()
            db.refresh(thread)
            return self._thread_response(thread)

    def ensure_thread(self, thread_id: str | None, client_id: str | None = None) -> ChatThreadResponse:
        """Return an existing thread or create one for backward-compatible clients."""

        if thread_id:
            with self.session_factory() as db:
                thread = db.get(ChatThread, thread_id)
                if thread:
                    return self._thread_response(thread)

        return self.create_thread(client_id or "default-client", thread_id=thread_id)

    def list_threads(self, client_id: str) -> list[ChatThreadResponse]:
        """List threads for one browser client, newest first."""

        with self.session_factory() as db:
            threads = (
                db.execute(
                    select(ChatThread)
                    .where(ChatThread.client_id == client_id)
                    .order_by(ChatThread.updated_at.desc())
                )
                .scalars()
                .all()
            )
            return [self._thread_response(thread) for thread in threads]

    def get_messages(self, thread_id: str, limit: int | None = None) -> list[ChatMessageResponse]:
        """Read visible messages for a thread in chronological order."""

        with self.session_factory() as db:
            statement = (
                select(ChatMessage)
                .where(ChatMessage.thread_id == thread_id)
                .order_by(ChatMessage.created_at.desc())
            )
            if limit:
                statement = statement.limit(limit)
            messages = list(reversed(db.execute(statement).scalars().all()))
            return [self._message_response(message) for message in messages]

    def add_message(
        self, *, thread_id: str, role: str, content: str, mode: str | None = None
    ) -> ChatMessageResponse:
        """Persist one chat message and touch the parent thread timestamp."""

        with self.session_factory() as db:
            message = ChatMessage(
                thread_id=thread_id,
                role=role,
                content=content,
                mode=mode,
            )
            db.add(message)
            thread = db.get(ChatThread, thread_id)
            if thread:
                if role == "user" and thread.title == "New chat":
                    thread.title = content[:80]
                db.add(thread)
            db.commit()
            db.refresh(message)
            return self._message_response(message)

    def add_turn(
        self, *, thread_id: str, user_message: str, assistant_message: str, mode: str
    ) -> None:
        """Persist a complete user/assistant exchange."""

        with self.session_factory() as db:
            db.add(ChatMessage(thread_id=thread_id, role="user", content=user_message))
            db.add(
                ChatMessage(
                    thread_id=thread_id,
                    role="assistant",
                    content=assistant_message,
                    mode=mode,
                )
            )
            thread = db.get(ChatThread, thread_id)
            if thread:
                if thread.title == "New chat":
                    thread.title = user_message[:80]
                db.add(thread)
            db.commit()

    def get_memory(self, thread_id: str) -> ThreadMemoryResponse:
        """Return persisted summary and facts for the prompt memory block."""

        with self.session_factory() as db:
            memory = db.get(ThreadMemory, thread_id)
            if not memory:
                memory = ThreadMemory(thread_id=thread_id, summary="", facts={})
                db.add(memory)
                db.commit()
                db.refresh(memory)
            return ThreadMemoryResponse(
                thread_id=memory.thread_id,
                summary=memory.summary,
                facts=memory.facts or {},
                updated_at=memory.updated_at,
            )

    def update_memory(self, *, thread_id: str, summary: str, facts: dict) -> ThreadMemoryResponse:
        """Upsert rolling summary and stable facts for a thread."""

        with self.session_factory() as db:
            memory = db.get(ThreadMemory, thread_id)
            if not memory:
                memory = ThreadMemory(thread_id=thread_id)
            memory.summary = summary
            memory.facts = facts
            db.add(memory)
            db.commit()
            db.refresh(memory)
            return ThreadMemoryResponse(
                thread_id=memory.thread_id,
                summary=memory.summary,
                facts=memory.facts or {},
                updated_at=memory.updated_at,
            )

    def _thread_response(self, thread: ChatThread) -> ChatThreadResponse:
        return ChatThreadResponse(
            thread_id=thread.id,
            client_id=thread.client_id,
            title=thread.title,
            created_at=thread.created_at,
            updated_at=thread.updated_at,
        )

    def _message_response(self, message: ChatMessage) -> ChatMessageResponse:
        return ChatMessageResponse(
            id=message.id,
            thread_id=message.thread_id,
            role=message.role,
            content=message.content,
            mode=message.mode,
            created_at=message.created_at,
        )
