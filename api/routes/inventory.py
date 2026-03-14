"""Inventory endpoints — read snapshots and update actuals (feedback loop)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.dependencies import get_db
from api.schemas import (
    ForecastAccuracyItem,
    InventoryItem,
    InventoryResponse,
    InventoryUpdateRequest,
    InventoryUpdateResponse,
)

router = APIRouter(prefix="/inventory", tags=["Inventory"])


@router.get("", response_model=InventoryResponse)
async def get_inventory(
    store_id: int = Query(..., ge=1),
    product_id: int | None = Query(None, ge=1),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    store = db.execute(
        text("SELECT store_id FROM stores WHERE store_id = :sid"), {"sid": store_id}
    ).first()
    if not store:
        raise HTTPException(status_code=404, detail=f"Store {store_id} not found")

    query = """
        SELECT
            i.product_id,
            p.name as product_name,
            c.name as category,
            i.quantity_on_hand,
            i.days_until_expiry,
            i.reorder_point
        FROM inventory_snapshots i
        JOIN products p ON p.product_id = i.product_id
        JOIN categories c ON c.category_id = p.category_id
        WHERE i.store_id = :sid
          AND i.date = (SELECT MAX(date) FROM inventory_snapshots WHERE store_id = :sid)
    """
    params: dict = {"sid": store_id}

    if product_id is not None:
        query += " AND i.product_id = :pid"
        params["pid"] = product_id

    query += " ORDER BY i.days_until_expiry ASC NULLS LAST LIMIT :lim OFFSET :off"
    params["lim"] = limit
    params["off"] = offset

    rows = db.execute(text(query), params).mappings().all()

    items = [
        InventoryItem(
            product_id=r["product_id"],
            product_name=r["product_name"],
            category=r["category"],
            quantity_on_hand=r["quantity_on_hand"],
            days_until_expiry=r["days_until_expiry"],
            waste_risk_score=None,
            waste_risk_tier=None,
            predicted_demand_today=None,
            reorder_point=r["reorder_point"],
        )
        for r in rows
    ]

    count_result = db.execute(
        text("""
            SELECT COUNT(*) FROM inventory_snapshots
            WHERE store_id = :sid
              AND date = (SELECT MAX(date) FROM inventory_snapshots WHERE store_id = :sid)
        """),
        {"sid": store_id},
    ).scalar()

    return InventoryResponse(
        store_id=store_id,
        items=items,
        total_items=count_result or 0,
        limit=limit,
        offset=offset,
    )


@router.post("/update", response_model=InventoryUpdateResponse)
async def update_inventory(
    req: InventoryUpdateRequest,
    db: Session = Depends(get_db),
):
    forecast_accuracy: dict[str, ForecastAccuracyItem] = {}

    for item in req.items:
        pred_row = (
            db.execute(
                text("""
                SELECT predicted_demand, model_version FROM predictions
                WHERE store_id = :sid AND product_id = :pid AND date = :dt
                ORDER BY created_at DESC LIMIT 1
            """),
                {"sid": req.store_id, "pid": item.product_id, "dt": str(req.date)},
            )
            .mappings()
            .first()
        )

        if pred_row:
            predicted = float(pred_row["predicted_demand"])
            error_pct = abs(predicted - item.actual_sold) / max(item.actual_sold, 1) * 100
            forecast_accuracy[f"product_{item.product_id}"] = ForecastAccuracyItem(
                predicted=round(predicted, 1),
                actual=item.actual_sold,
                error_pct=round(error_pct, 1),
            )

            db.execute(
                text("""
                    UPDATE predictions
                    SET actual_demand = :actual, forecast_error = :err
                    WHERE store_id = :sid AND product_id = :pid AND date = :dt
                      AND model_version = :mv
                """),
                {
                    "actual": item.actual_sold,
                    "err": round((predicted - item.actual_sold) / max(item.actual_sold, 1), 4),
                    "sid": req.store_id,
                    "pid": item.product_id,
                    "dt": str(req.date),
                    "mv": pred_row["model_version"],
                },
            )

    db.commit()

    mape_row = (
        db.execute(
            text("""
            SELECT AVG(ABS(forecast_error)) as avg_mape
            FROM predictions
            WHERE store_id = :sid
              AND actual_demand IS NOT NULL
              AND date >= CAST(:dt AS date) - INTERVAL '7 days'
        """),
            {"sid": req.store_id, "dt": str(req.date)},
        )
        .mappings()
        .first()
    )

    rolling_mape = (
        round(float(mape_row["avg_mape"]) * 100, 1) if mape_row and mape_row["avg_mape"] else None
    )

    return InventoryUpdateResponse(
        store_id=req.store_id,
        date=req.date,
        items_updated=len(forecast_accuracy),
        forecast_accuracy=forecast_accuracy,
        rolling_7d_mape=rolling_mape,
    )
