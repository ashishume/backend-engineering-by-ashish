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
