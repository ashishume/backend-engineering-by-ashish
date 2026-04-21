from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.user import UserCreate, UserResponse
from app.services.user_service import create_user, get_users

router = APIRouter()


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create(user: UserCreate, db: AsyncSession = Depends(get_db)) -> UserResponse:
    return await create_user(db, user)


@router.get("/", response_model=list[UserResponse])
async def read(db: AsyncSession = Depends(get_db)) -> list[UserResponse]:
    return await get_users(db)