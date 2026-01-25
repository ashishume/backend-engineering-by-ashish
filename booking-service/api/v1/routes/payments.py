from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from schemas.payments.transactions import TransactionCreate, TransactionResponse
from schemas.payments.bank_account import PaymentCreate, PaymentResponse
from database import get_db
from services.payments.payments_service import PaymentsService

router = APIRouter()


@router.post("/", description="create payment", status_code=status.HTTP_201_CREATED)
async def create_payments(
    request: Request, payload: TransactionCreate, db: Session = Depends(get_db)
) -> TransactionResponse:
    service = PaymentsService(db)
    payments = await service.create_payments(payload)

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
