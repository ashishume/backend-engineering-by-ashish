from fastapi import APIRouter, Depends, Request, status, Header
from sqlalchemy.orm import Session
from typing import Annotated
from schemas.payments.transactions import TransactionCreate, TransactionResponse
from schemas.payments.bank_account import PaymentCreate, PaymentResponse
from database import get_db
from services.payments.payments_service import PaymentsService

router = APIRouter()


@router.post(
    "/",
    description="create payment. Supports idempotency via 'Idempotency-Key' header or payload field.",
    status_code=status.HTTP_201_CREATED
)
async def create_payments(
    request: Request,
    payload: TransactionCreate,
    db: Session = Depends(get_db),
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> TransactionResponse:
    """
    Create a payment transaction.
    
    Supports idempotency to prevent duplicate transactions:
    - Send 'Idempotency-Key' header with a unique value (e.g., UUID)
    - Or include 'idempotency_key' in the request body
    - If the same key is used again, the original transaction response is returned
    
    Example:
        Headers: Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000
    """
    service = PaymentsService(db)
    payments = await service.create_payments(payload, idempotency_key=idempotency_key)
    return payments


@router.post(
    "/account", description="create account", status_code=status.HTTP_201_CREATED
)
async def create_account(
    request: Request, payload: PaymentCreate, db: Session = Depends(get_db)
) -> PaymentResponse:
    service = PaymentsService(db)
    payments = await service.create_bank_account(payload)

    return payments
