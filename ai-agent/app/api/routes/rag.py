from __future__ import annotations

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse

from app.langchain_rag.service import LangChainGraphRagService
from app.schemas.rag import (
    ChatThreadResponse,
    CreateThreadRequest,
    DeleteDocumentResponse,
    ListMessagesResponse,
    ListThreadsResponse,
    ListDocumentsResponse,
    RagChatRequest,
    RagChatResponse,
    UploadDocumentResponse,
)
from app.services.rag_service import RagService

router = APIRouter(prefix="/rag", tags=["RAG"])


def get_rag_service(request: Request) -> RagService:
    return request.app.state.rag_service


def get_langchain_rag_service(request: Request) -> LangChainGraphRagService:
    return request.app.state.langchain_rag_service


@router.post("/documents", response_model=UploadDocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    use_langchain: bool = Form(False),
    service: RagService = Depends(get_rag_service),
    langchain_service: LangChainGraphRagService = Depends(get_langchain_rag_service),
):
    try:
        active_service = langchain_service if use_langchain else service
        document = await active_service.index_document(file)
        return UploadDocumentResponse(document=document)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/documents", response_model=ListDocumentsResponse)
async def list_documents(service: RagService = Depends(get_rag_service)):
    return ListDocumentsResponse(documents=service.list_documents())


@router.delete("/documents/{document_id}", response_model=DeleteDocumentResponse)
async def delete_document(
    document_id: str,
    service: RagService = Depends(get_rag_service),
):
    deleted = service.delete_document(document_id)
    return DeleteDocumentResponse(document_id=document_id, deleted=deleted)


@router.post("/threads", response_model=ChatThreadResponse)
async def create_thread(
    request: CreateThreadRequest,
    service: RagService = Depends(get_rag_service),
):
    return service.create_thread(client_id=request.client_id, title=request.title)


@router.get("/threads", response_model=ListThreadsResponse)
async def list_threads(
    client_id: str,
    service: RagService = Depends(get_rag_service),
):
    return ListThreadsResponse(threads=service.list_threads(client_id=client_id))


@router.get("/threads/{thread_id}/messages", response_model=ListMessagesResponse)
async def get_thread_messages(
    thread_id: str,
    service: RagService = Depends(get_rag_service),
):
    return ListMessagesResponse(messages=service.get_thread_messages(thread_id=thread_id))


@router.post("/chat", response_model=RagChatResponse)
async def chat(
    request: RagChatRequest,
    service: RagService = Depends(get_rag_service),
    langchain_service: LangChainGraphRagService = Depends(get_langchain_rag_service),
):
    try:
        active_service = langchain_service if request.use_langchain else service
        return await active_service.chat(
            session_id=request.session_id,
            thread_id=request.thread_id,
            client_id=request.client_id,
            message=request.message,
            top_k=request.top_k,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/chat/stream")
async def stream_chat(
    request: RagChatRequest,
    service: RagService = Depends(get_rag_service),
    langchain_service: LangChainGraphRagService = Depends(get_langchain_rag_service),
):
    active_service = langchain_service if request.use_langchain else service
    return StreamingResponse(
        active_service.stream_chat(
            session_id=request.session_id,
            thread_id=request.thread_id,
            client_id=request.client_id,
            message=request.message,
            top_k=request.top_k,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
