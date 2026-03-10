"""FastAPI application factory for ShelfLife AI."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.dependencies import get_model_manager
from api.middleware import AuthMiddleware, RateLimitMiddleware, RequestLoggingMiddleware
from api.routes import forecast, health, inventory, recommend, waste
from config.settings import settings

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting ShelfLife AI API...")
    mm = get_model_manager()
    mm.load()
    logger.info("Models loaded: %s", mm.is_loaded)
    yield
    logger.info("Shutting down ShelfLife AI API...")


app = FastAPI(
    title="ShelfLife AI",
    description="Production ML platform for demand forecasting and food waste reduction",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RateLimitMiddleware, max_requests=settings.rate_limit_per_minute)
app.add_middleware(AuthMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(forecast.router)
app.include_router(waste.router)
app.include_router(recommend.router)
app.include_router(inventory.router)
