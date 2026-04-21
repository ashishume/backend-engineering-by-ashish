from fastapi import APIRouter
from app.api.v1.endpoints import user
from app.api.v1.endpoints import search
api_router = APIRouter()
api_router.include_router(user.router, prefix="/users", tags=["Users"])
api_router.include_router(search.router, prefix="/search", tags=["Search"])
