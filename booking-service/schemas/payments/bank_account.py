import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class PaymentCreate(BaseModel):
    account_number: str
    name: str
    account_status: str


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    account_number: str
    account_status: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
