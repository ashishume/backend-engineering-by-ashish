from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.multi_agent import router as multi_agent_router
from app.api.routes.notion_agent import router as notion_agent_router
from app.api.routes.rag import router as rag_router
from app.core.clients import build_openrouter_client, build_qdrant_client
from app.core.config import settings
from app.db.database import SessionLocal, init_db
from app.langchain_rag.service import LangChainGraphRagService
from app.multi_agent.service import MultiAgentCustomerService
from app.notion_agent.client import NotionClient
from app.notion_agent.service import NotionAgentService
from app.notion_agent.vector_store import NotionVectorStore
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
notion_vector_store = NotionVectorStore(
    client=qdrant_client,
    collection_name=settings.notion_qdrant_collection,
)
thread_repository = ThreadRepository(SessionLocal)
embedding_service = EmbeddingService(
    client=openrouter_client,
    model=settings.embedding_model,
    batch_size=settings.embedding_batch_size,
)
rag_service = RagService(
    settings=settings,
    llm_client=openrouter_client,
    loader=loader,
    chunker=TextChunker(
        chunk_size=settings.chunk_token_size,
        chunk_overlap=settings.chunk_token_overlap,
    ),
    embeddings=embedding_service,
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
app.state.multi_agent_service = MultiAgentCustomerService(
    settings=settings,
    embeddings=rag_service.embeddings,
    vector_store=manual_vector_store,
    memory=SessionMemoryService(token_limit=settings.memory_token_limit),
    thread_repository=thread_repository,
)
app.state.notion_agent_service = NotionAgentService(
    settings=settings,
    notion_client=NotionClient(settings),
    embeddings=embedding_service,
    vector_store=notion_vector_store,
    chunker=TextChunker(
        chunk_size=settings.chunk_token_size,
        chunk_overlap=settings.chunk_token_overlap,
    ),
    memory=SessionMemoryService(token_limit=settings.memory_token_limit),
    thread_repository=thread_repository,
)

app.include_router(rag_router)
app.include_router(multi_agent_router)
app.include_router(notion_agent_router)


@app.on_event("startup")
def on_startup():
    init_db()
    if settings.notion_sync_on_startup:
        try:
            app.state.notion_agent_service.sync_notion()
        except Exception as exc:
            print(f"Notion startup sync skipped: {exc}")


@app.get("/", tags=["Health"])
async def root():
    return {
        "status": "ok",
        "message": "RAG Assistant API is running",
        "qdrant_collection": settings.qdrant_collection,
        "chat_model": settings.chat_model,
        "embedding_model": settings.embedding_model,
        "openrouter_configured": bool(settings.openrouter_api_key),
        "notion_configured": bool(settings.notion_api_key),
        "notion_collection": settings.notion_qdrant_collection,
    }


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}
