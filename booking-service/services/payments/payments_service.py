from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from repository.payments.payments_repo import PaymentsRepo
from schemas.payments.transactions import TransactionCreate, TransactionResponse
from schemas.payments.bank_account import PaymentCreate, PaymentResponse
from models.payments.bank_account import BankAccount
from models.payments.transactions import Transaction
from core.redis_client import get_redis
import json
import logging

logger = logging.getLogger(__name__)


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

    async def create_payments(self, payload: TransactionCreate, idempotency_key: str | None = None):
        """
        Create a payment transaction with idempotency support.
        
        Args:
            payload: Transaction creation payload
            idempotency_key: Optional idempotency key from header or payload
            
        Returns:
            TransactionResponse: The created or existing transaction
        """
        # Use idempotency key from parameter (header) or payload
        idempotency_key = idempotency_key or payload.idempotency_key
        
        # If idempotency key is provided, check for existing transaction
        if idempotency_key:
            # Check Redis cache first (fast path)
            redis_client = await get_redis()
            if redis_client:
                try:
                    cached_response = await redis_client.get(f"idempotency:{idempotency_key}")
                    if cached_response:
                        logger.info(f"Returning cached response for idempotency key: {idempotency_key}")
                        return TransactionResponse.model_validate_json(cached_response)
                except Exception as e:
                    logger.warning(f"Redis cache check failed: {e}. Continuing with database check.")
            
            # Check database for existing transaction
            existing_transaction = self.repository.get_transaction_by_idempotency_key(idempotency_key)
            if existing_transaction:
                logger.info(f"Found existing transaction for idempotency key: {idempotency_key}")
                response = TransactionResponse.model_validate(existing_transaction)
                
                # Cache the response in Redis for future requests
                if redis_client:
                    try:
                        await redis_client.setex(
                            f"idempotency:{idempotency_key}",
                            86400,  # 24 hours TTL
                            response.model_dump_json()
                        )
                    except Exception as e:
                        logger.warning(f"Failed to cache response in Redis: {e}")
                
                return response
        
        try:
            # Validate business rules
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

            # Create Transaction object from payload
            # Ensure idempotency_key is set if provided
            transaction_data = payload.model_dump()
            if idempotency_key:
                transaction_data["idempotency_key"] = idempotency_key
            
            new_payload = Transaction(**transaction_data)

            # deduct amount from the sender first
            sender_deduction = self.repository.deduct_sender_amount(new_payload)

            receiver_deduction = self.repository.add_receiver_amount(new_payload)

            if not sender_deduction or not receiver_deduction:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to process payment deduction/addition",
                )

            payments = self.repository.make_payments(new_payload)

        except IntegrityError as e:
            self.db.rollback()
            error_msg = str(e.orig) if hasattr(e, "orig") else str(e)
            
            # Check if it's an idempotency key violation (duplicate key)
            if "idempotency_key" in error_msg.lower() or "unique constraint" in error_msg.lower():
                # This means another request with the same key was processed
                # Fetch and return the existing transaction
                if idempotency_key:
                    existing_transaction = self.repository.get_transaction_by_idempotency_key(idempotency_key)
                    if existing_transaction:
                        logger.info(f"Idempotency key conflict resolved - returning existing transaction: {idempotency_key}")
                        response = TransactionResponse.model_validate(existing_transaction)
                        
                        # Cache the response
                        redis_client = await get_redis()
                        if redis_client:
                            try:
                                await redis_client.setex(
                                    f"idempotency:{idempotency_key}",
                                    86400,
                                    response.model_dump_json()
                                )
                            except Exception as e:
                                logger.warning(f"Failed to cache response in Redis: {e}")
                        
                        return response
                    else:
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail="Idempotency key conflict but transaction not found",
                        )
            
            # Check if it's a foreign key constraint violation
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
        except HTTPException:
            # Re-raise HTTP exceptions as-is
            raise
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

        response = TransactionResponse.model_validate(payments)
        
        # Cache successful response in Redis
        if idempotency_key:
            redis_client = await get_redis()
            if redis_client:
                try:
                    await redis_client.setex(
                        f"idempotency:{idempotency_key}",
                        86400,  # 24 hours TTL
                        response.model_dump_json()
                    )
                    logger.info(f"Cached transaction response for idempotency key: {idempotency_key}")
                except Exception as e:
                    logger.warning(f"Failed to cache response in Redis: {e}")

        return response
