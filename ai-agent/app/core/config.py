from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Application settings read from environment variables.

    Keeping settings in one object makes the rest of the service easy to test:
    tests can construct `Settings` directly instead of patching `os.environ`.
    """

    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "")
    openrouter_base_url: str = os.getenv(
        "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
    )
    openrouter_http_referer: str = os.getenv(
        "OPENROUTER_HTTP_REFERER", "http://localhost:5173"
    )
    openrouter_app_title: str = os.getenv(
        "OPENROUTER_APP_TITLE", "Backend Engineering RAG"
    )
    chat_model: str = os.getenv("CHAT_MODEL", "openai/gpt-4o-mini")
    embedding_model: str = os.getenv(
        "EMBEDDING_MODEL", "openai/text-embedding-3-small"
    )

    qdrant_url: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    qdrant_api_key: str | None = os.getenv("QDRANT_API_KEY") or None
    qdrant_collection: str = os.getenv("QDRANT_COLLECTION", "rag_documents")

    notion_api_key: str = os.getenv("NOTION_API_KEY", "")
    notion_version: str = os.getenv("NOTION_VERSION", "2026-03-11")
    notion_sync_on_startup: bool = (
        os.getenv("NOTION_SYNC_ON_STARTUP", "true").lower() == "true"
    )
    notion_qdrant_collection: str = os.getenv(
        "NOTION_QDRANT_COLLECTION", "notion_memory"
    )
    notion_max_pages: int = int(os.getenv("NOTION_MAX_PAGES", "100"))

    postgres_user: str = os.getenv("POSTGRES_USER", "postgres")
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "admin")
    postgres_db: str = os.getenv("POSTGRES_DB", "ai_agent")
    postgres_host: str = os.getenv("POSTGRES_HOST", "localhost")
    postgres_port: str = os.getenv("POSTGRES_PORT", "5439")
    database_url: str = os.getenv(
        "AI_AGENT_DATABASE_URL",
        (
            f"postgresql://{postgres_user}:{postgres_password}"
            f"@{postgres_host}:{postgres_port}/{postgres_db}"
        ),
    )

    chunk_token_size: int = int(os.getenv("CHUNK_TOKEN_SIZE", "800"))
    chunk_token_overlap: int = int(os.getenv("CHUNK_TOKEN_OVERLAP", "120"))
    embedding_batch_size: int = int(os.getenv("EMBEDDING_BATCH_SIZE", "32"))
    default_top_k: int = int(os.getenv("DEFAULT_TOP_K", "6"))
    max_top_k: int = int(os.getenv("MAX_TOP_K", "12"))
    retrieval_score_threshold: float = float(
        os.getenv("RETRIEVAL_SCORE_THRESHOLD", "0.35")
    )
    memory_token_limit: int = int(os.getenv("MEMORY_TOKEN_LIMIT", "6000"))
    memory_recent_messages_limit: int = int(os.getenv("MEMORY_RECENT_MESSAGES_LIMIT", "24"))
    max_upload_mb: int = int(os.getenv("MAX_UPLOAD_MB", "25"))


settings = Settings()
