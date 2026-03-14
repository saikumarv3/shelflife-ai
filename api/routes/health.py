"""Health, readiness, and Prometheus metrics endpoints."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Response
from sqlalchemy import text

from api.dependencies import ModelManager, get_model_manager, get_redis
from api.schemas import HealthResponse, ReadyResponse
from db.session import engine

try:
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
except ImportError:
    generate_latest = None
    CONTENT_TYPE_LATEST = "text/plain"

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="healthy", timestamp=datetime.now(timezone.utc))


@router.get("/ready", response_model=ReadyResponse)
async def ready(mm: ModelManager = Depends(get_model_manager)):
    checks: dict[str, str] = {}

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["database"] = "connected"
    except Exception:
        checks["database"] = "connection_refused"

    try:
        r = get_redis()
        r.ping()
        checks["redis"] = "connected"
    except Exception:
        checks["redis"] = "connection_refused"

    if mm.is_loaded:
        checks["demand_model"] = f"loaded ({mm.model_version})"
        checks["waste_model"] = f"loaded ({mm.model_version})"
    else:
        checks["demand_model"] = "not_loaded"
        checks["waste_model"] = "not_loaded"

    all_ok = all("refused" not in v and "not_" not in v for v in checks.values())
    status_code = 200 if all_ok else 503

    return Response(
        content=ReadyResponse(
            status="ready" if all_ok else "not_ready",
            checks=checks,
            timestamp=datetime.now(timezone.utc),
        ).model_dump_json(),
        status_code=status_code,
        media_type="application/json",
    )


@router.get("/metrics")
async def metrics():
    if generate_latest is None:
        return Response(content="prometheus_client not installed", media_type="text/plain")
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
