from sqlalchemy import Column, UUID, DateTime, Float, String, ForeignKey
from database import Base
import uuid
import datetime
from enum import Enum


class TransactionStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    from_bank_account_id = Column(
        UUID(as_uuid=True), ForeignKey("bank_accounts.id"), nullable=False
    )
    to_bank_account_id = Column(
        UUID(as_uuid=True), ForeignKey("bank_accounts.id"), nullable=False
    )
    amount = Column(Float, nullable=False)
    currency = Column(String(255), nullable=False)
    status = Column(String(255), default=TransactionStatus.PENDING, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )
