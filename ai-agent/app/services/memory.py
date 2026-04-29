from __future__ import annotations

from llama_index.core.llms import ChatMessage
from llama_index.core.memory import Memory

from app.schemas.rag import ChatMessageResponse


class SessionMemoryService:
    """In-process LlamaIndex memory registry keyed by browser session id."""

    def __init__(self, token_limit: int):
        self.token_limit = token_limit
        self._memories: dict[str, Memory] = {}

    def get_memory(self, session_id: str) -> Memory:
        """Return a token-limited memory object for a session."""

        if session_id not in self._memories:
            self._memories[session_id] = Memory.from_defaults(
                session_id=session_id,
                token_limit=self.token_limit,
            )
        return self._memories[session_id]

    def hydrate_memory(
        self, session_id: str, messages: list[ChatMessageResponse]
    ) -> Memory:
        """Create a LlamaIndex memory object from persisted Postgres messages.

        Hydration only happens on first access for a thread. After that, new
        turns are appended to both LlamaIndex and Postgres.
        """
        if session_id not in self._memories:
            memory = Memory.from_defaults(
                session_id=session_id,
                token_limit=self.token_limit,
            )
            if messages:
                memory.put_messages(
                    [
                        ChatMessage(role=message.role, content=message.content)
                        for message in messages
                    ]
                )
            self._memories[session_id] = memory
        return self._memories[session_id]

    async def get_messages(self, session_id: str) -> list[dict[str, str]]:
        """Load memory messages and convert them to OpenRouter chat format."""

        memory = self.get_memory(session_id)
        messages = await memory.aget()
        return [self._to_openrouter_message(message) for message in messages]

    def get_messages_sync(
        self,
        session_id: str,
        persisted_messages: list[ChatMessageResponse] | None = None,
    ) -> list[dict[str, str]]:
        """Synchronous memory read for thread-pooled streaming responses."""

        memory = (
            self.hydrate_memory(session_id, persisted_messages)
            if persisted_messages is not None
            else self.get_memory(session_id)
        )
        messages = memory.get()
        return [self._to_openrouter_message(message) for message in messages]

    async def add_turn(
        self, session_id: str, user_message: str, assistant_message: str
    ) -> None:
        """Store a user/assistant exchange while allowing Memory to enforce limits."""

        memory = self.get_memory(session_id)
        await memory.aput_messages(
            [
                ChatMessage(role="user", content=user_message),
                ChatMessage(role="assistant", content=assistant_message),
            ]
        )

    def add_turn_sync(
        self, session_id: str, user_message: str, assistant_message: str
    ) -> None:
        """Synchronous memory write used after a streamed answer completes."""

        memory = self.get_memory(session_id)
        memory.put_messages(
            [
                ChatMessage(role="user", content=user_message),
                ChatMessage(role="assistant", content=assistant_message),
            ]
        )

    def _to_openrouter_message(self, message: ChatMessage) -> dict[str, str]:
        """Convert LlamaIndex chat messages to plain chat-completion messages."""

        content = getattr(message, "content", None)
        if content is None and getattr(message, "blocks", None):
            content = "\n".join(str(block) for block in message.blocks)

        role = str(message.role)
        if "." in role:
            role = role.rsplit(".", 1)[-1]
        return {"role": role.lower(), "content": str(content or "")}
