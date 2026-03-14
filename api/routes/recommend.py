"""Recommendation endpoint — generates ranked actions."""

from __future__ import annotations

import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.dependencies import ModelManager, get_db, get_model_manager
from api.schemas import ActionImpact, Recommendation, RecommendRequest, RecommendResponse
from monitoring.metrics import RECOMMENDATIONS_GENERATED
from recommendation.engine import RecommendationEngine

router = APIRouter(tags=["Recommendations"])
_engine = RecommendationEngine()


@router.post("/recommend", response_model=RecommendResponse)
async def recommend(
    req: RecommendRequest,
    db: Session = Depends(get_db),
    mm: ModelManager = Depends(get_model_manager),
):
    if not mm.is_loaded:
        raise HTTPException(status_code=503, detail="Model not available, try again later")

    product = (
        db.execute(
            text("SELECT name, unit_price, cost_price FROM products WHERE product_id = :pid"),
            {"pid": req.product_id},
        )
        .mappings()
        .first()
    )
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {req.product_id} not found")

    inv = (
        db.execute(
            text("""
            SELECT quantity_on_hand, days_until_expiry FROM inventory_snapshots
            WHERE store_id = :sid AND product_id = :pid
            ORDER BY date DESC LIMIT 1
        """),
            {"sid": req.store_id, "pid": req.product_id},
        )
        .mappings()
        .first()
    )

    current_stock = int(inv["quantity_on_hand"]) if inv else 0
    days_exp = int(inv["days_until_expiry"] or 7) if inv else 7

    feature_row = (
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

    if feature_row is None:
        raise HTTPException(status_code=404, detail="No features available")

    cols = mm.feature_columns
    vector = [float(feature_row.get(c, 0) or 0) for c in cols]
    X = np.array([vector], dtype=np.float32)

    demand_result = mm.predict_demand(X)
    predicted_demand = float(demand_result["predicted_demand"][0])

    proba, tiers = mm.predict_waste_risk(X)
    risk_score = float(proba[0])
    risk_tier = tiers[0]

    raw_recs = _engine.generate(
        store_id=req.store_id,
        product_id=req.product_id,
        product_name=product["name"],
        waste_risk_score=risk_score,
        predicted_demand=predicted_demand,
        current_stock=current_stock,
        unit_price=float(product["unit_price"]),
        cost_price=float(product["cost_price"]),
        days_until_expiry=days_exp,
    )

    recommendations = [
        Recommendation(
            action=r["action"],
            priority=r["priority"],
            description=r["description"],
            expected_impact=ActionImpact(**r["expected_impact"]),
            confidence=r["confidence"],
        )
        for r in raw_recs
    ]

    for rec in recommendations:
        RECOMMENDATIONS_GENERATED.labels(action_type=rec.action).inc()

    return RecommendResponse(
        store_id=req.store_id,
        product_id=req.product_id,
        date=req.date,
        recommendations=recommendations,
        waste_risk_score=round(risk_score, 3),
        waste_risk_tier=risk_tier,
    )
