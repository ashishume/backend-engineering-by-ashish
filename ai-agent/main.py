from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.rag import router as rag_router
from app.core.clients import build_openrouter_client, build_qdrant_client
from app.core.config import settings
from app.db.database import SessionLocal, init_db
from app.langchain_rag.service import LangChainGraphRagService
from app.repositories.thread_repository import ThreadRepository
from app.services.chunker import TextChunker
from app.services.document_loader import DocumentLoader
from app.services.embeddings import EmbeddingService
from app.services.memory import SessionMemoryService
from app.services.rag_service import RagService
from app.services.vector_store import QdrantVectorStore

app = FastAPI(
    title="RAG Assistant API",
    description="FastAPI RAG service using OpenRouter, Qdrant, and LlamaIndex Memory",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

openrouter_client = build_openrouter_client()
qdrant_client = build_qdrant_client()
loader = DocumentLoader()
manual_vector_store = QdrantVectorStore(
    client=qdrant_client,
    collection_name=settings.qdrant_collection,
)
thread_repository = ThreadRepository(SessionLocal)
rag_service = RagService(
    settings=settings,
    llm_client=openrouter_client,
    loader=loader,
    chunker=TextChunker(
        chunk_size=settings.chunk_token_size,
        chunk_overlap=settings.chunk_token_overlap,
    ),
    embeddings=EmbeddingService(
        client=openrouter_client,
        model=settings.embedding_model,
        batch_size=settings.embedding_batch_size,
    ),
    vector_store=manual_vector_store,
    memory=SessionMemoryService(token_limit=settings.memory_token_limit),
    thread_repository=thread_repository,
)
app.state.rag_service = rag_service
app.state.langchain_rag_service = LangChainGraphRagService(
    settings=settings,
    qdrant_client=qdrant_client,
    loader=loader,
    manual_vector_store=manual_vector_store,
    memory=SessionMemoryService(token_limit=settings.memory_token_limit),
    thread_repository=thread_repository,
)

app.include_router(rag_router)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/", tags=["Health"])
async def root():
    return {
        "status": "ok",
        "message": "RAG Assistant API is running",
        "qdrant_collection": settings.qdrant_collection,
        "chat_model": settings.chat_model,
        "embedding_model": settings.embedding_model,
        "openrouter_configured": bool(settings.openrouter_api_key),
    }


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}
