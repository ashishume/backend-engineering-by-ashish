import io
import math
import os
import re
import uuid
from pathlib import Path
from typing import Any

import chromadb
from docx import Document
from dotenv import load_dotenv
from fastapi import APIRouter, File, Query, UploadFile
from langchain_text_splitters import RecursiveCharacterTextSplitter
from openai import OpenAI
from pypdf import PdfReader

load_dotenv()

# booking-service/v2/api/documents.py -> parents[2] == booking-service
_CHROMA_DIR = Path(__file__).resolve().parents[2] / ".chroma_data"
_CHROMA_DIR.mkdir(parents=True, exist_ok=True)

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_KEY"),
)

# Default in-memory Client() drops all vectors on process restart (--reload).
chroma_client = chromadb.PersistentClient(path=str(_CHROMA_DIR))
collection = chroma_client.get_or_create_collection("documents")

# OpenRouter expects vendor-prefixed model ids for chat.
CHAT_MODEL = os.getenv("OPENROUTER_CHAT_MODEL", "openai/gpt-4o-mini")

EMBEDDING_MODEL = "openai/text-embedding-3-small"
# semantic: split where consecutive sentences are dissimilar in embedding space
# recursive: fixed-size RecursiveCharacterTextSplitter (no extra embed calls on upload)
DOCUMENT_CHUNKING_STRATEGY = os.getenv("DOCUMENT_CHUNKING_STRATEGY", "semantic").lower()
# Below this cosine similarity between adjacent sentences, start a new chunk (tune 0.35–0.65).
DOCUMENT_SEMANTIC_SIMILARITY_THRESHOLD = float(
    os.getenv("DOCUMENT_SEMANTIC_SIMILARITY_THRESHOLD", "0.5")
)
# Cap sentence-level embedding calls; beyond this, fall back to recursive splitting.
_DOCUMENT_SEMANTIC_MAX_SENTENCES = int(os.getenv("DOCUMENT_SEMANTIC_MAX_SENTENCES", "800"))
_CHUNK_SIZE = int(os.getenv("DOCUMENT_CHUNK_SIZE", "1000"))
_CHUNK_OVERLAP = int(os.getenv("DOCUMENT_CHUNK_OVERLAP", "200"))

router = APIRouter()


def get_embedding(text: str) -> list[float]:
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text,
    )
    return response.data[0].embedding


def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Batch embeddings for semantic chunking (OpenAI-compatible API)."""
    if not texts:
        return []
    batch_size = 64
    out: list[list[float]] = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        response = client.embeddings.create(model=EMBEDDING_MODEL, input=batch)
        ordered = sorted(response.data, key=lambda d: d.index)
        out.extend(item.embedding for item in ordered)
    return out


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def _split_into_sentences(text: str) -> list[str]:
    """Lightweight sentence split (no extra NLP deps); best for prose-style PDFs/DOCX."""
    text = text.strip()
    if not text:
        return []
    parts = re.split(r"(?<=[.!?。！？])\s+", text)
    return [p.strip() for p in parts if p.strip()]


def _recursive_split(text: str) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=_CHUNK_SIZE,
        chunk_overlap=_CHUNK_OVERLAP,
    )
    return splitter.split_text(text)


def semantic_split_docs(text: str) -> list[str]:
    """Chunk by embedding similarity between adjacent sentences (topic / boundary aware)."""
    sentences = _split_into_sentences(text)
    if not sentences:
        return []
    if len(sentences) == 1:
        return _recursive_split(sentences[0]) if len(sentences[0]) > _CHUNK_SIZE else sentences

    if len(sentences) > _DOCUMENT_SEMANTIC_MAX_SENTENCES:
        return _recursive_split(text)

    embeddings = get_embeddings_batch(sentences)
    if len(embeddings) != len(sentences):
        return _recursive_split(text)

    spans: list[tuple[int, int]] = []
    start = 0
    thr = DOCUMENT_SEMANTIC_SIMILARITY_THRESHOLD
    for i in range(len(sentences) - 1):
        if _cosine_similarity(embeddings[i], embeddings[i + 1]) < thr:
            spans.append((start, i + 1))
            start = i + 1
    spans.append((start, len(sentences)))

    merged = [" ".join(sentences[s:e]) for s, e in spans]
    final: list[str] = []
    for chunk in merged:
        if len(chunk) > _CHUNK_SIZE:
            final.extend(_recursive_split(chunk))
        else:
            final.append(chunk)
    return final


def store_chunks(chunks: list[str]) -> None:
    batch_id = uuid.uuid4().hex[:12]
    for i, chunk in enumerate(chunks):
        embedding = get_embedding(chunk)
        collection.add(
            ids=[f"{batch_id}_{i}"],
            documents=[chunk],
            embeddings=[embedding],
            metadatas=[{"source": "uploaded_file"}],
        )


def extract_text(filename: str | None, content: bytes) -> str:
    name = filename or ""
    if name.endswith(".pdf"):
        reader = PdfReader(io.BytesIO(content))
        return "\n".join([page.extract_text() or "" for page in reader.pages])

    if name.endswith(".docx"):
        doc = Document(io.BytesIO(content))
        return "\n".join([p.text for p in doc.paragraphs])

    if name.endswith(".txt"):
        return content.decode()

    raise ValueError("Unsupported file type")


def split_docs(text: str) -> list[str]:
    if DOCUMENT_CHUNKING_STRATEGY == "recursive":
        return _recursive_split(text)
    return semantic_split_docs(text)


def retrieve(query: str, k: int = 3) -> list[str]:
    if collection.count() == 0:
        return []
    query_embedding = get_embedding(query)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(k, max(collection.count(), 1)),
    )
    docs_batch = results.get("documents") or []
    if not docs_batch or not docs_batch[0]:
        return []
    return [d for d in docs_batch[0] if d]


def build_prompt(query: str, docs: list[str]) -> str:
    context = "\n\n".join(docs)

    return f"""
You are a helpful assistant.
Answer ONLY from the given context.
If not found, say "I don't know".

Context:
{context}

Question:
{query}
"""


def generate_answer(prompt: str) -> str:
    res = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    return res.choices[0].message.content


def _normalize_query(query: str) -> str:
    q = query.strip()
    if len(q) >= 2 and q[0] == q[-1] and q[0] in "\"'":
        return q[1:-1].strip()
    return q


def _rows_from_chroma_get(
    raw: dict[str, Any],
    include_embeddings: bool,
) -> list[dict[str, Any]]:
    ids = raw.get("ids") or []
    docs = raw.get("documents") or []
    metas = raw.get("metadatas") or []
    embs = raw.get("embeddings") if include_embeddings else None
    rows: list[dict[str, Any]] = []
    for i, cid in enumerate(ids):
        row: dict[str, Any] = {
            "id": cid,
            "text": docs[i] if i < len(docs) else None,
            "metadata": metas[i] if i < len(metas) else None,
        }
        if include_embeddings and embs is not None and i < len(embs):
            row["embedding"] = embs[i]
        rows.append(row)
    return rows


@router.get("/chunks", response_model=dict[str, Any])
def list_chunks(
    limit: int | None = Query(
        default=None,
        ge=1,
        le=50_000,
        description="Page size; omit to return every chunk (may be large).",
    ),
    offset: int = Query(default=0, ge=0, description="Skip this many chunks (pagination)."),
    include_embeddings: bool = Query(
        default=False,
        description="Include embedding vectors (large JSON).",
    ),
) -> dict[str, Any]:
    """Return stored vector-db rows: id, text, metadata (and optionally embeddings)."""
    total = collection.count()
    include: list[str] = ["documents", "metadatas"]
    if include_embeddings:
        include.append("embeddings")

    if limit is None:
        batch_size = 500
        rows = []
        o = 0
        while True:
            raw = collection.get(include=include, limit=batch_size, offset=o)
            part = _rows_from_chroma_get(raw, include_embeddings)
            if not part:
                break
            rows.extend(part)
            o += len(part)
            if len(part) < batch_size:
                break
        return {"total": total, "count": len(rows), "chunks": rows}

    raw = collection.get(include=include, limit=limit, offset=offset)
    rows = _rows_from_chroma_get(raw, include_embeddings)
    return {"total": total, "count": len(rows), "chunks": rows}


@router.post("/upload", response_model=dict[str, Any])
async def upload_document(file: UploadFile = File(...)) -> dict[str, Any]:
    content = await file.read()
    text = extract_text(file.filename, content)

    chunks = split_docs(text)
    store_chunks(chunks)

    return {
        "message": "File processed successfully",
        "chunks_stored": len(chunks),
        "chroma_count": collection.count(),
    }


@router.post("/ask")
def ask(
    query: str = Query(..., description="Question; answered from ingested document chunks"),
) -> dict[str, Any]:
    q = _normalize_query(query)
    docs = retrieve(q)
    prompt = build_prompt(q, docs)
    answer = generate_answer(prompt)

    return {
        "answer": answer,
        "context": docs,
        "chunks_used": len(docs),
        "chroma_count": collection.count(),
    }
