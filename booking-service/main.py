"""Main FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError

from database import Base, DATABASE_URL, engine
import models

# import v2.models
from api.v1.routes import (
    # theaters,
    movies,
    # showings,
    # seats,
    # booking,
    # booking_seats,
    # search,
    # payments,
)

from v2.api import search, llm_apis

# from core.utils import auth_guard
# from core.elasticsearch_client import (
#     get_elasticsearch_client,
#     close_elasticsearch_client,
#     create_index_if_not_exists,
# )
# from core.elasticsearch_indices import ELASTICSEARCH_INDICES, get_all_index_names
# from api.v1.routes import upcoming_ipo_scrap
# from core.redis_client import connect_redis, close_redis

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("app.log")],
)

logger = logging.getLogger(__name__)


def _ensure_database_exists() -> None:
    """Create target database when running against a fresh local Postgres."""
    url = make_url(DATABASE_URL)
    db_name = url.database
    if not db_name:
        return

    admin_engine = create_engine(
        url.set(database="postgres"),
        pool_pre_ping=True,
        isolation_level="AUTOCOMMIT",
    )
    try:
        with admin_engine.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :db_name"),
                {"db_name": db_name},
            ).scalar()
            if not exists:
                safe_db_name = db_name.replace('"', '""')
                conn.execute(text(f'CREATE DATABASE "{safe_db_name}"'))
                logger.info("Created missing database '%s'", db_name)
    finally:
        admin_engine.dispose()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.

    This replaces the deprecated @app.on_event decorators.
    """
    # Startup
    logger.info("Starting up application...")
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except OperationalError as exc:
        if 'does not exist' not in str(exc):
            raise
        logger.warning("Target database missing. Attempting to create it...")
        _ensure_database_exists()
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    logger.info("Database connection check passed")
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")

    # Connect to Redis for caching and rate limiting
    # await connect_redis()

    yield

    # Shutdown
    logger.info("Shutting down application...")
    logger.info("Closing database connections...")
    engine.dispose()
    # logger.info("Closing Redis connection...")
    # await close_redis()
    logger.info("Application shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Booking Service",
    description="Booking Service for the booking management system",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# auth guard for all routes
# app.add_middleware(AuthMiddleware)


# Include routers
routes = [
    # (theaters.router, "/booking/theaters", ["theaters"], [Depends(auth_guard)]),
    (movies.router, "/movies", ["movies"], []),
    # (showings.router, "/booking/showings", ["showings"], [Depends(auth_guard)]),
    # (seats.router, "/booking/seats", ["seats"], [Depends(auth_guard)]),
    # (booking.router, "/booking/bookings", ["bookings"], [Depends(auth_guard)]),
    # (payments.router, "/booking/payments", ["payments"], []),
    # (
    #     booking_seats.router,
    #     "/booking/booking_seats",
    #     ["booking_seats"],
    #     [Depends(auth_guard)],
    # ),
    # (search.router, "/booking/search", ["search"], [Depends(auth_guard)]),
    # (upcoming_ipo_scrap.router, "/booking/scrap", ["scrap"], []),
    (search.router, "/search", ["search"], []),
    (llm_apis.router, "/documents", ["documents"], []),
]

for router, prefix, tags, dependencies in routes:
    app.include_router(router, prefix=prefix, tags=tags, dependencies=dependencies)


@app.get("/", tags=["root"])
async def root():
    return {
        "message": "Welcome to Booking Service",
        "status": "running",
        "docs": "/docs",
    }
