from fastapi import APIRouter
from app.api.v1.endpoints import user
from app.api.v1.endpoints import search
from app.api.v1.endpoints import books

api_router = APIRouter()
api_router.include_router(user.router, prefix="/users", tags=["Users"])
api_router.include_router(search.router, prefix="/search", tags=["Search"])
api_router.include_router(books.router, prefix="/books", tags=["Books"])
