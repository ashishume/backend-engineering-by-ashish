from __future__ import annotations

from openai import OpenAI


class EmbeddingService:
    """Generate vector embeddings through OpenRouter's OpenAI-compatible API."""

    def __init__(self, client: OpenAI, model: str, batch_size: int):
        self.client = client
        self.model = model
        self.batch_size = batch_size

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed many texts in stable batches.

        Batching protects the API from very large request payloads while
        preserving input order, which is important because vectors are zipped
        back onto chunk metadata during indexing.
        """

        vectors: list[list[float]] = []
        if self.client.api_key == "missing-openrouter-api-key":
            raise ValueError("OPENROUTER_API_KEY is required before indexing or chat")

        for start in range(0, len(texts), self.batch_size):
            batch = texts[start : start + self.batch_size]
            response = self.client.embeddings.create(model=self.model, input=batch)
            ordered = sorted(response.data, key=lambda item: item.index)
            vectors.extend([item.embedding for item in ordered])
        return vectors

    def embed_query(self, query: str) -> list[float]:
        """Embed a single user query for vector retrieval."""

        return self.embed_texts([query])[0]
