"""Demand forecast endpoints — single and batch prediction."""

from __future__ import annotations

import json
import time
from datetime import date as _date

import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.dependencies import ModelManager, get_db, get_model_manager, get_redis
from api.schemas import (
    BatchDemandRequest,
    BatchDemandResponse,
    DemandRequest,
    DemandResponse,
)
from config.settings import settings
from monitoring.metrics import CACHE_HITS, CACHE_MISSES

router = APIRouter(prefix="/predict", tags=["Forecast"])


def _cache_key(store_id: int, product_id: int, date_str: str) -> str:
    return f"demand:{store_id}:{product_id}:{date_str}"


def _cache_ttl(prediction_date: _date) -> int:
    """Return TTL in seconds: shorter for today (data may update), longer for future dates."""
    if prediction_date > _date.today():
        return settings.cache_ttl_future
    return settings.cache_ttl_same_day


def _build_feature_vector(db: Session, req: DemandRequest, mm: ModelManager) -> np.ndarray:
    """Look up pre-computed features from feature_store, or return zeros as fallback."""
    row = (
        db.execute(
            text("""
            SELECT * FROM feature_store
            WHERE store_id = :sid AND product_id = :pid AND date = :dt
            LIMIT 1
        """),
            {"sid": req.store_id, "pid": req.product_id, "dt": str(req.date)},
        )
        .mappings()
        .first()
    )

    if row is None:
        last_row = (
            db.execute(
                text("""
                SELECT * FROM feature_store
                WHERE store_id = :sid AND product_id = :pid
                ORDER BY date DESC LIMIT 1
            """),
                {"sid": req.store_id, "pid": req.product_id},
            )
            .mappings()
            .first()
        )
        if last_row is None:
            raise HTTPException(
                status_code=404,
                detail=f"No features for store {req.store_id}, product {req.product_id}",
            )
        row = last_row

    cols = mm.feature_columns
    vector = [float(row.get(c, 0) or 0) for c in cols]
    return np.array([vector], dtype=np.float32)


@router.post("/demand", response_model=DemandResponse)
async def predict_demand(
    req: DemandRequest,
    db: Session = Depends(get_db),
    mm: ModelManager = Depends(get_model_manager),
):
    if not mm.is_loaded:
        raise HTTPException(status_code=503, detail="Model not available, try again later")

    start = time.perf_counter()
    cache_k = _cache_key(req.store_id, req.product_id, str(req.date))

    try:
        r = get_redis()
        cached = r.get(cache_k)
        if cached:
            CACHE_HITS.inc()
            data = json.loads(cached)
            data["cached"] = True
            data["latency_ms"] = round((time.perf_counter() - start) * 1000, 1)
            return DemandResponse(**data)
    except Exception:
        pass

    CACHE_MISSES.inc()
    X = _build_feature_vector(db, req, mm)
    result = mm.predict_demand(X)

    response_data = {
        "store_id": req.store_id,
        "product_id": req.product_id,
        "date": str(req.date),
        "predicted_demand": round(float(result["predicted_demand"][0]), 1),
        "confidence_lower": round(float(result["confidence_lower"][0]), 1),
        "confidence_upper": round(float(result["confidence_upper"][0]), 1),
        "model_version": mm.model_version,
        "cached": False,
        "latency_ms": round((time.perf_counter() - start) * 1000, 1),
    }

    try:
        r = get_redis()
        r.setex(cache_k, _cache_ttl(req.date), json.dumps(response_data))
    except Exception:
        pass

    return DemandResponse(**response_data)


@router.post("/batch", response_model=BatchDemandResponse)
async def predict_batch(
    req: BatchDemandRequest,
    db: Session = Depends(get_db),
    mm: ModelManager = Depends(get_model_manager),
):
    if not mm.is_loaded:
        raise HTTPException(status_code=503, detail="Model not available, try again later")

    start = time.perf_counter()
    results = []
    cache_hits = 0

    for item in req.predictions:
        cache_k = _cache_key(item.store_id, item.product_id, str(item.date))
        cached = None
        try:
            r = get_redis()
            cached = r.get(cache_k)
        except Exception:
            pass

        if cached:
            data = json.loads(cached)
            data["cached"] = True
            data["latency_ms"] = 0
            results.append(DemandResponse(**data))
            cache_hits += 1
            continue

        X = _build_feature_vector(db, item, mm)
        result = mm.predict_demand(X)

        resp = DemandResponse(
            store_id=item.store_id,
            product_id=item.product_id,
            date=item.date,
            predicted_demand=round(float(result["predicted_demand"][0]), 1),
            confidence_lower=round(float(result["confidence_lower"][0]), 1),
            confidence_upper=round(float(result["confidence_upper"][0]), 1),
            model_version=mm.model_version,
            cached=False,
            latency_ms=0,
        )
        results.append(resp)

        try:
            r = get_redis()
            r.setex(cache_k, _cache_ttl(item.date), resp.model_dump_json())
        except Exception:
            pass

    total = len(req.predictions)
    return BatchDemandResponse(
        results=results,
        total_items=total,
        cache_hit_rate=round(cache_hits / total, 2) if total else 0,
        total_latency_ms=round((time.perf_counter() - start) * 1000, 1),
    )
