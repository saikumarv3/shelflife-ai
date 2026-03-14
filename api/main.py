"""FastAPI application factory for ShelfLife AI."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.dependencies import get_model_manager
from api.middleware import AuthMiddleware, RateLimitMiddleware, RequestLoggingMiddleware
from api.routes import forecast, health, inventory, recommend, waste
from config.settings import settings
from monitoring.metrics import MODEL_VERSION

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def _job_daily_forecast():
    from scripts.run_daily_forecast import run

    run()


def _job_drift_check():
    from db.session import engine
    from mlops.drift_detection import run_drift_check

    run_drift_check(engine)


def _job_feedback():
    from scripts.run_feedback import run

    run()


def _job_retrain():
    from db.session import engine
    from mlops.retrain import retrain_and_validate, should_retrain

    triggers = should_retrain(engine)
    if triggers["should_retrain"]:
        retrain_and_validate(engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting ShelfLife AI API...")
    mm = get_model_manager()
    mm.load()
    if mm.is_loaded:
        MODEL_VERSION.labels(model_name=settings.demand_model_name, version=mm.model_version).set(1)
    logger.info("Models loaded: %s", mm.is_loaded)

    scheduler.add_job(_job_daily_forecast, "cron", hour=6, minute=0, id="daily_forecast")
    scheduler.add_job(_job_drift_check, "cron", hour=23, minute=0, id="drift_check")
    scheduler.add_job(_job_feedback, "cron", hour=23, minute=30, id="feedback")
    scheduler.add_job(_job_retrain, "cron", day_of_week="sun", hour=2, minute=0, id="retrain")
    scheduler.start()
    logger.info("Scheduler started with 4 jobs")

    yield

    scheduler.shutdown(wait=False)
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
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(forecast.router)
app.include_router(waste.router)
app.include_router(recommend.router)
app.include_router(inventory.router)
