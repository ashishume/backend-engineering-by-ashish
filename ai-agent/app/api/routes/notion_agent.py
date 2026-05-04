from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.notion_agent.service import NotionAgentService
from app.schemas.notion_agent import (
    ListNotionSourcesResponse,
    NotionAgentChatRequest,
    NotionAgentChatResponse,
    NotionSyncResponse,
)

router = APIRouter(prefix="/notion-agent", tags=["Notion Agent"])


def get_notion_agent_service(request: Request) -> NotionAgentService:
    return request.app.state.notion_agent_service


@router.post("/sync", response_model=NotionSyncResponse)
def sync_notion(
    service: NotionAgentService = Depends(get_notion_agent_service),
):
    try:
        return service.sync_notion()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Notion sync failed: {exc}",
        )


@router.get("/sources", response_model=ListNotionSourcesResponse)
def list_notion_sources(
    service: NotionAgentService = Depends(get_notion_agent_service),
):
    return ListNotionSourcesResponse(sources=service.list_sources())


@router.post("/chat", response_model=NotionAgentChatResponse)
async def notion_chat(
    request: NotionAgentChatRequest,
    service: NotionAgentService = Depends(get_notion_agent_service),
):
    try:
        return await service.chat(
            session_id=request.session_id,
            thread_id=request.thread_id,
            client_id=request.client_id,
            message=request.message,
            top_k=request.top_k,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
