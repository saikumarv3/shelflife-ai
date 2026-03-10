"""Waste risk prediction endpoint."""

from __future__ import annotations

import time

import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.dependencies import get_db, get_model_manager, ModelManager
from api.schemas import WasteRiskRequest, WasteRiskResponse
from recommendation.engine import RecommendationEngine

router = APIRouter(prefix="/predict", tags=["Waste Risk"])


@router.post("/waste-risk", response_model=WasteRiskResponse)
async def predict_waste_risk(
    req: WasteRiskRequest,
    db: Session = Depends(get_db),
    mm: ModelManager = Depends(get_model_manager),
):
    if not mm.is_loaded:
        raise HTTPException(status_code=503, detail="Model not available, try again later")

    row = db.execute(
        text("""
            SELECT * FROM feature_store
            WHERE store_id = :sid AND product_id = :pid
            ORDER BY ABS(date - CAST(:dt AS date)) LIMIT 1
        """),
        {"sid": req.store_id, "pid": req.product_id, "dt": str(req.date)},
    ).mappings().first()

    if row is None:
        raise HTTPException(status_code=404, detail=f"No features for store {req.store_id}, product {req.product_id}")

    cols = mm.feature_columns
    vector = []
    for c in cols:
        if c == "days_until_expiry_norm":
            shelf_days = float(row.get("shelf_life_days", 7) or 7)
            vector.append(req.days_until_expiry / max(shelf_days, 1))
        elif c == "stock_to_sales_ratio":
            avg_sales = float(row.get("sales_rolling_7d_mean", 1) or 1)
            vector.append(req.current_stock / max(avg_sales, 0.1))
        else:
            vector.append(float(row.get(c, 0) or 0))

    X = np.array([vector], dtype=np.float32)

    demand_result = mm.predict_demand(X)
    predicted_demand = float(demand_result["predicted_demand"][0])

    proba, tiers = mm.predict_waste_risk(X)
    risk_score = float(proba[0])
    risk_tier = tiers[0]

    excess = max(0, req.current_stock - int(predicted_demand))
    markdown_pct = RecommendationEngine._compute_markdown_pct(risk_score, req.days_until_expiry)
    explanation = _build_explanation(
        risk_tier, req.days_until_expiry, req.current_stock,
        predicted_demand, markdown_pct,
    )

    return WasteRiskResponse(
        store_id=req.store_id,
        product_id=req.product_id,
        date=req.date,
        waste_risk_score=round(risk_score, 3),
        waste_risk_tier=risk_tier,
        predicted_demand=round(predicted_demand, 1),
        excess_stock=excess,
        recommended_markdown_pct=markdown_pct,
        explanation=explanation,
        model_version=mm.model_version,
    )


def _build_explanation(tier: str, days_exp: int, stock: int, demand: float, md: int) -> str:
    tier_label = tier.capitalize()
    parts = [f"{tier_label} risk: {days_exp} days until expiry with {stock} units on hand."]
    parts.append(f"Historical velocity suggests ~{int(demand)} units/day sellthrough.")
    if md > 0:
        parts.append(f"Consider {md}% markdown to accelerate sales.")
    return " ".join(parts)
