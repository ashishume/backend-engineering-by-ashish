from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from uuid import uuid4

from qdrant_client import QdrantClient
from qdrant_client.http import models

from app.schemas.rag import DocumentMetadata, SourceChunk


class QdrantVectorStore:
    """Qdrant-backed vector storage for document chunks."""

    def __init__(self, client: QdrantClient, collection_name: str):
        self.client = client
        self.collection_name = collection_name

    def ensure_collection(self, vector_size: int) -> None:
        """Create the collection if needed using cosine similarity.

        If the collection already exists, Qdrant validates vector dimensions at
        upsert time. A dimension mismatch usually means the embedding model was
        changed and the collection should be recreated or migrated.
        """

        if self.client.collection_exists(self.collection_name):
            return

        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=models.VectorParams(
                size=vector_size,
                distance=models.Distance.COSINE,
            ),
        )

    def upsert_document(
        self,
        *,
        document_id: str,
        filename: str,
        source_type: str,
        chunks: list[str],
        vectors: list[list[float]],
    ) -> DocumentMetadata:
        """Persist document chunks and their vectors in Qdrant."""

        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors must have the same length")
        if not vectors:
            raise ValueError("at least one vector is required")

        self.ensure_collection(len(vectors[0]))
        created_at = datetime.now(timezone.utc)
        points = []

        for chunk_index, (chunk, vector) in enumerate(zip(chunks, vectors)):
            points.append(
                models.PointStruct(
                    id=str(uuid4()),
                    vector=vector,
                    payload={
                        "document_id": document_id,
                        "filename": filename,
                        "source_type": source_type,
                        "chunk_index": chunk_index,
                        "text": chunk,
                        "created_at": created_at.isoformat(),
                    },
                )
            )

        self.client.upsert(collection_name=self.collection_name, points=points)
        return DocumentMetadata(
            document_id=document_id,
            filename=filename,
            source_type=source_type,
            chunk_count=len(chunks),
            created_at=created_at,
        )

    def search(self, query_vector: list[float], top_k: int) -> list[SourceChunk]:
        """Return the most similar chunks for a query vector."""

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

        sources: list[SourceChunk] = []
        for point in points:
            payload = point.payload or {}
            sources.append(
                SourceChunk(
                    document_id=str(payload.get("document_id", "")),
                    filename=str(payload.get("filename", "")),
                    chunk_index=int(payload.get("chunk_index", 0)),
                    text=str(payload.get("text", "")),
                    score=float(point.score or 0.0),
                )
            )
        return sources

    def list_documents(self) -> list[DocumentMetadata]:
        """Build a document list from chunk payloads stored in Qdrant."""

        if not self.client.collection_exists(self.collection_name):
            return []

        docs: dict[str, dict] = defaultdict(
            lambda: {
                "filename": "",
                "source_type": "",
                "chunk_count": 0,
                "created_at": None,
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
                document_id = str(payload.get("document_id", ""))
                if not document_id:
                    continue
                docs[document_id]["filename"] = payload.get("filename", "")
                docs[document_id]["source_type"] = payload.get("source_type", "")
                docs[document_id]["chunk_count"] += 1
                docs[document_id]["created_at"] = payload.get("created_at")
            if offset is None:
                break

        result: list[DocumentMetadata] = []
        for document_id, data in docs.items():
            created_at_raw = data["created_at"]
            created_at = (
                datetime.fromisoformat(created_at_raw)
                if created_at_raw
                else datetime.now(timezone.utc)
            )
            result.append(
                DocumentMetadata(
                    document_id=document_id,
                    filename=data["filename"],
                    source_type=data["source_type"],
                    chunk_count=data["chunk_count"],
                    created_at=created_at,
                )
            )

        return sorted(result, key=lambda doc: doc.created_at, reverse=True)

    def delete_document(self, document_id: str) -> bool:
        """Delete every chunk that belongs to a document id."""

        if not self.client.collection_exists(self.collection_name):
            return False

        self.client.delete(
            collection_name=self.collection_name,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="document_id",
                            match=models.MatchValue(value=document_id),
                        )
                    ]
                )
            ),
        )
        return True
