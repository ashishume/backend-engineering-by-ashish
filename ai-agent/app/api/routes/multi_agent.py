from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.multi_agent.service import MultiAgentCustomerService
from app.schemas.rag import MultiAgentChatRequest, MultiAgentChatResponse

router = APIRouter(prefix="/multi-agent", tags=["Multi Agent"])


def get_multi_agent_service(request: Request) -> MultiAgentCustomerService:
    return request.app.state.multi_agent_service


@router.post("/chat", response_model=MultiAgentChatResponse)
async def customer_chat(
    request: MultiAgentChatRequest,
    service: MultiAgentCustomerService = Depends(get_multi_agent_service),
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
