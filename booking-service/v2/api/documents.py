import io
import os
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

router = APIRouter()


def get_embedding(text: str) -> list[float]:
    response = client.embeddings.create(
        model="openai/text-embedding-3-small",
        input=text,
    )
    return response.data[0].embedding


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
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    return splitter.split_text(text)


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
