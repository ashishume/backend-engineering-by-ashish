from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from uuid import uuid4

from qdrant_client import QdrantClient
from qdrant_client.http import models

from app.schemas.notion_agent import NotionSourceChunk, NotionSourcePage


class NotionVectorStore:
    """Qdrant storage isolated to chunks sourced from Notion pages."""

    def __init__(self, client: QdrantClient, collection_name: str):
        self.client = client
        self.collection_name = collection_name

    def ensure_collection(self, vector_size: int) -> None:
        if self.client.collection_exists(self.collection_name):
            return

        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=models.VectorParams(
                size=vector_size,
                distance=models.Distance.COSINE,
            ),
        )

    def upsert_page(
        self,
        *,
        page_id: str,
        page_title: str,
        url: str,
        last_edited_time: str | None,
        chunks: list[str],
        vectors: list[list[float]],
    ) -> int:
        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors must have the same length")
        if not vectors:
            return 0

        self.ensure_collection(len(vectors[0]))
        self.delete_page(page_id)
        indexed_at = datetime.now(timezone.utc).isoformat()
        points = []

        for chunk_index, (chunk, vector) in enumerate(zip(chunks, vectors)):
            points.append(
                models.PointStruct(
                    id=str(uuid4()),
                    vector=vector,
                    payload={
                        "page_id": page_id,
                        "page_title": page_title,
                        "url": url,
                        "chunk_index": chunk_index,
                        "text": chunk,
                        "source_type": "notion",
                        "last_edited_time": last_edited_time,
                        "indexed_at": indexed_at,
                    },
                )
            )

        self.client.upsert(collection_name=self.collection_name, points=points)
        return len(points)

    def search(self, query_vector: list[float], top_k: int) -> list[NotionSourceChunk]:
        try:
            response = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                limit=top_k,
                with_payload=True,
            )
            points = response.points
        except AttributeError:
            points = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=top_k,
                with_payload=True,
            )
        except Exception as exc:
            if "Not found" in str(exc) or "doesn't exist" in str(exc):
                return []
            raise

        sources: list[NotionSourceChunk] = []
        for point in points:
            payload = point.payload or {}
            sources.append(
                NotionSourceChunk(
                    page_id=str(payload.get("page_id", "")),
                    page_title=str(payload.get("page_title", "")),
                    url=str(payload.get("url", "")),
                    chunk_index=int(payload.get("chunk_index") or 0),
                    text=str(payload.get("text", "")),
                    score=float(point.score or 0.0),
                )
            )
        return sources

    def list_pages(self) -> list[NotionSourcePage]:
        if not self.client.collection_exists(self.collection_name):
            return []

        pages: dict[str, dict] = defaultdict(
            lambda: {
                "page_title": "",
                "url": "",
                "chunk_count": 0,
                "last_edited_time": None,
                "indexed_at": None,
            }
        )
        offset = None

        while True:
            points, offset = self.client.scroll(
                collection_name=self.collection_name,
                limit=100,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            for point in points:
                payload = point.payload or {}
                page_id = str(payload.get("page_id") or "")
                if not page_id:
                    continue
                pages[page_id]["page_title"] = str(payload.get("page_title") or "")
                pages[page_id]["url"] = str(payload.get("url") or "")
                pages[page_id]["chunk_count"] += 1
                pages[page_id]["last_edited_time"] = payload.get("last_edited_time")
                pages[page_id]["indexed_at"] = payload.get("indexed_at")
            if offset is None:
                break

        result: list[NotionSourcePage] = []
        for page_id, data in pages.items():
            result.append(
                NotionSourcePage(
                    page_id=page_id,
                    page_title=data["page_title"],
                    url=data["url"],
                    chunk_count=data["chunk_count"],
                    last_edited_time=_parse_datetime(data["last_edited_time"]),
                    indexed_at=_parse_datetime(data["indexed_at"])
                    or datetime.now(timezone.utc),
                )
            )
        return sorted(result, key=lambda page: page.indexed_at, reverse=True)

    def delete_page(self, page_id: str) -> bool:
        if not self.client.collection_exists(self.collection_name):
            return False

        self.client.delete(
            collection_name=self.collection_name,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="page_id",
                            match=models.MatchValue(value=page_id),
                        )
                    ]
                )
            ),
        )
        return True


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
