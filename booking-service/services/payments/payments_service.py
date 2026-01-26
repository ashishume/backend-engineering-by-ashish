from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from repository.payments.payments_repo import PaymentsRepo
from schemas.payments.transactions import TransactionCreate, TransactionResponse
from schemas.payments.bank_account import PaymentCreate, PaymentResponse
from models.payments.bank_account import BankAccount
from models.payments.transactions import Transaction


class PaymentsService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = PaymentsRepo(db)

    async def create_bank_account(self, payload: PaymentCreate):

        # create validations for payments like if from and to should not be same
        # amount should not be 0 or negative
        # currency should be within the given list of currencies
        # to and from account should exist (in the db)

        new_payload = BankAccount(**payload.model_dump())

        try:
            payments = self.repository.create_accounts(new_payload)
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Account with this account number already exists",
            )
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Account creation failed: {str(e)}",
            )

        if payments is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account creation failed",
            )

        return PaymentResponse.model_validate(payments)

    async def create_payments(self, payload: TransactionCreate):
        try:
            if payload.from_bank_account_id == payload.to_bank_account_id:
                raise HTTPException(
                    detail="Sender and reciever cannot be same",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            if payload.amount == 0:
                raise HTTPException(
                    detail="Amount cannot be zero",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            if not self.repository.check_if_accounts_exist(payload):
                raise HTTPException(
                    detail="Accounts doesnt exist",
                    status_code=status.HTTP_404_NOT_FOUND,
                )

            new_payload = Transaction(**payload.model_dump())

            payments = self.repository.make_payments(new_payload)
        except IntegrityError as e:
            self.db.rollback()
            # Check if it's a foreign key constraint violation
            error_msg = str(e.orig) if hasattr(e, "orig") else str(e)
            if (
                "foreign key" in error_msg.lower()
                or "bank_accounts" in error_msg.lower()
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid bank account ID. One or both bank accounts do not exist.",
                )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Transaction creation failed due to constraint violation",
            )
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Payment creation failed: {str(e)}",
            )

        if payments is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Payments failed"
            )

        return TransactionResponse.model_validate(payments)
