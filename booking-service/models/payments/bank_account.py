import datetime
from sqlalchemy import Column, UUID, DateTime, Float, String
import uuid
from database import Base
from enum import Enum


class BankAccountStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    BLOCKED = "blocked"
    FROZEN = "frozen"


class BankAccount(Base):
    __tablename__ = "bank_accounts"
    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    name = Column(
        String(255),
        nullable=False,
    )
    account_number = Column(
        String(255),
        nullable=False,
        unique=True,
    )
    account_status = Column(
        String(255),
        nullable=False,
        default=BankAccountStatus.ACTIVE,
    )
    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.datetime.utcnow,
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )
