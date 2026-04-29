from __future__ import annotations

from openai import OpenAI
from qdrant_client import QdrantClient

from app.core.config import Settings, settings


def build_openrouter_client(config: Settings = settings) -> OpenAI:
    """Create an OpenAI-compatible client that sends requests to OpenRouter."""

    return OpenAI(
        api_key=config.openrouter_api_key or "missing-openrouter-api-key",
        base_url=config.openrouter_base_url,
        default_headers={
            "HTTP-Referer": config.openrouter_http_referer,
            "X-Title": config.openrouter_app_title,
        },
    )


def build_qdrant_client(config: Settings = settings) -> QdrantClient:
    """Create the Qdrant client used by the vector store service."""

    return QdrantClient(
        url=config.qdrant_url,
        api_key=config.qdrant_api_key,
        check_compatibility=False,
    )
