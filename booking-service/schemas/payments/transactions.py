from pydantic import BaseModel, ConfigDict
from uuid import UUID
from models.payments.transactions import TransactionStatus
import datetime


class TransactionCreate(BaseModel):
    from_bank_account_id: UUID
    to_bank_account_id: UUID
    amount: float
    currency: str
    status: str


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    from_bank_account_id: UUID
    to_bank_account_id: UUID
    amount: float
    currency: str
    status: TransactionStatus
    created_at: datetime.datetime
    updated_at: datetime.datetime


class BankAccountDetailsCreate(BaseModel):
    name: str
    account_number: str
    account_status: str


class BankAccountDetailsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    account_number: str
    account_status: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
