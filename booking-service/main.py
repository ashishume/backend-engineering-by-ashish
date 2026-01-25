"""Main FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import Base, engine
import models
from api.v1.routes import (
    theaters,
    movies,
    showings,
    seats,
    booking,
    booking_seats,
    search,
    payments,
)
from core.utils import auth_guard
from core.elasticsearch_client import (
    get_elasticsearch_client,
    close_elasticsearch_client,
    create_index_if_not_exists,
)
from core.elasticsearch_indices import ELASTICSEARCH_INDICES, get_all_index_names
from api.v1.routes import upcoming_ipo_scrap
from core.redis_client import connect_redis, close_redis

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("app.log")],
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.

    This replaces the deprecated @app.on_event decorators.
    """
    # Startup
    logger.info("Starting up application...")
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")

    # Connect to Redis for caching and rate limiting
    await connect_redis()

    # Initialize Elasticsearch client
    logger.info("Initializing Elasticsearch client...")
    try:
        get_elasticsearch_client()
        logger.info("Elasticsearch client initialized successfully")

        # Create all Elasticsearch indices
        logger.info("Setting up Elasticsearch indices...")
        for index_name in get_all_index_names():
            index_config = ELASTICSEARCH_INDICES[index_name]
            create_index_if_not_exists(
                index_name=index_name, mapping=index_config["mappings"]
            )
        logger.info("Elasticsearch indices setup complete")
    except Exception as e:
        logger.warning(f"Failed to initialize Elasticsearch client: {str(e)}")

    yield

    # Shutdown
    logger.info("Shutting down application...")
    logger.info("Closing database connections...")
    engine.dispose()
    logger.info("Closing Redis connection...")
    await close_redis()
    logger.info("Closing Elasticsearch client...")
    close_elasticsearch_client()
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
    (theaters.router, "/booking/theaters", ["theaters"], [Depends(auth_guard)]),
    (movies.router, "/booking/movies", ["movies"], [Depends(auth_guard)]),
    (showings.router, "/booking/showings", ["showings"], [Depends(auth_guard)]),
    (seats.router, "/booking/seats", ["seats"], [Depends(auth_guard)]),
    (booking.router, "/booking/bookings", ["bookings"], [Depends(auth_guard)]),
    (payments.router, "/booking/payments", ["payments"], []),
    (
        booking_seats.router,
        "/booking/booking_seats",
        ["booking_seats"],
        [Depends(auth_guard)],
    ),
    (search.router, "/booking/search", ["search"], [Depends(auth_guard)]),
    (upcoming_ipo_scrap.router, "/booking/scrap", ["scrap"], []),
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
