from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import init_db
from app.models import user  # noqa: F401

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        await init_db()
    except (SQLAlchemyError, OSError) as exc:
        logger.warning("Database initialization skipped: %s", exc)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/", tags=["Health"])
async def root() -> dict[str, str]:
    return {"message": f"{settings.APP_NAME} is running"}