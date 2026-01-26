import stat
from fastapi import HTTPException, status
from sqlalchemy import Select, select
from models.payments.transactions import Transaction
from sqlalchemy.orm import Session
from schemas.payments.transactions import TransactionCreate, TransactionResponse
from models.payments.bank_account import BankAccount
from models.payments.transactions import Transaction


class PaymentsRepo:
    def __init__(self, db: Session):
        self.db = db

    def create_accounts(self, accounts: BankAccount):
        self.db.add(accounts)
        self.db.commit()
        self.db.refresh(accounts)

        return accounts

    def make_payments(self, transaction: Transaction):

        # check the idempotency keys for transactions

        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)

        return transaction

    def deduct_sender_amount(self, payload: Transaction):
        try:
            sender = self.db.execute(
                select(BankAccount).where(
                    BankAccount.id == payload.from_bank_account_id
                )
            ).scalar_one_or_none()

            if not sender:
                raise HTTPException(
                    detail="Details not found", status_code=status.HTTP_404_NOT_FOUND
                )

            if sender.balance >= payload.amount:
                sender.balance = sender.balance - payload.amount
            else:
                raise HTTPException(
                    detail="Not sufficient balance",
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )
            self.db.commit()
            self.db.refresh(sender)

            return sender
        except Exception as e:
            raise HTTPException(
                detail=f"failed error {e}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def add_receiver_amount(self, payload: Transaction):
        try:
            receiver = self.db.execute(
                select(BankAccount).where(BankAccount.id == payload.to_bank_account_id)
            ).scalar_one_or_none()

            if not receiver:
                raise HTTPException(
                    detail="Details not found", status_code=status.HTTP_404_NOT_FOUND
                )

            receiver.balance = receiver.balance + payload.amount

            self.db.commit()
            self.db.refresh(receiver)

            return receiver
        except:
            raise HTTPException(
                detail="internal server error",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def check_if_accounts_exist(self, payload: TransactionCreate):
        try:
            accounts = (
                self.db.execute(
                    select(BankAccount).where(
                        BankAccount.id.in_(
                            [payload.from_bank_account_id, payload.to_bank_account_id]
                        )
                    )
                )
                .scalars()
                .all()
            )
            # Return True only if both accounts exist (exactly 2 accounts found)
            return len(accounts) == 2
        except:
            raise HTTPException(
                detail="internal server error",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
