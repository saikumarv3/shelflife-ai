"""Lightweight visitor tracking for ChotuLab landing page.

Stores location, user-agent, referrer, and timestamp in PostgreSQL.
No API key required — this endpoint is public but rate-limited.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from db.models import SiteVisit
from db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["analytics"])


class VisitPayload(BaseModel):
    source: Optional[str] = Field(None, max_length=20)
    ip: Optional[str] = Field(None, max_length=45)
    city: Optional[str] = Field(None, max_length=100)
    region: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    path: Optional[str] = Field(None, max_length=256)
    referrer: Optional[str] = Field(None, max_length=256)


@router.post("/track-visit", status_code=201)
def track_visit(payload: VisitPayload, request: Request, db: Session = Depends(get_db)):
    xff = request.headers.get("X-Forwarded-For")
    real_ip = xff.split(",")[0].strip() if xff else (
        request.headers.get("X-Real-IP", "").strip()
        or (request.client.host if request.client else None)
    )

    visit = SiteVisit(
        source=payload.source,
        ip=payload.ip or real_ip,
        city=payload.city,
        region=payload.region,
        country=payload.country,
        latitude=payload.latitude,
        longitude=payload.longitude,
        user_agent=(request.headers.get("User-Agent") or "")[:512],
        path=payload.path,
        referrer=payload.referrer or request.headers.get("Referer", "")[:256],
        payload_json=payload.model_dump(exclude_none=True),
    )
    db.add(visit)
    db.commit()

    logger.info("Visit tracked: %s / %s, %s", payload.city, payload.country, payload.source)
    return {"ok": True}
