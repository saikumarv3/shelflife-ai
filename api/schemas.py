"""Pydantic request/response models for every API endpoint."""

import datetime as _dt
from typing import Literal

from pydantic import BaseModel, Field


# ── Demand forecast ──────────────────────────────────────────


class DemandRequest(BaseModel):
    store_id: int = Field(..., ge=1, description="Store identifier")
    product_id: int = Field(..., ge=1, description="Product identifier")
    date: _dt.date = Field(..., description="Target prediction date (YYYY-MM-DD)")


class DemandResponse(BaseModel):
    store_id: int
    product_id: int
    date: _dt.date
    predicted_demand: float = Field(..., ge=0)
    confidence_lower: float = Field(..., ge=0)
    confidence_upper: float = Field(..., ge=0)
    model_version: str
    cached: bool
    latency_ms: float


class BatchDemandRequest(BaseModel):
    predictions: list[DemandRequest] = Field(
        ..., min_length=1, max_length=500, description="Up to 500 predictions per batch"
    )


class BatchDemandResponse(BaseModel):
    results: list[DemandResponse]
    total_items: int
    cache_hit_rate: float
    total_latency_ms: float


# ── Waste risk ───────────────────────────────────────────────


class WasteRiskRequest(BaseModel):
    store_id: int = Field(..., ge=1)
    product_id: int = Field(..., ge=1)
    date: _dt.date
    current_stock: int = Field(..., ge=0, description="Units currently on shelf")
    days_until_expiry: int = Field(..., ge=0, description="Days until earliest expiry")


class WasteRiskResponse(BaseModel):
    store_id: int
    product_id: int
    date: _dt.date
    waste_risk_score: float = Field(..., ge=0.0, le=1.0)
    waste_risk_tier: Literal["low", "medium", "high", "critical"]
    predicted_demand: float
    excess_stock: int
    recommended_markdown_pct: int = Field(..., ge=0, le=80)
    explanation: str
    model_version: str


# ── Recommendations ──────────────────────────────────────────


class RecommendRequest(BaseModel):
    store_id: int = Field(..., ge=1)
    product_id: int = Field(..., ge=1)
    date: _dt.date


class ActionImpact(BaseModel):
    waste_reduction_units: int
    revenue_impact_usd: float
    waste_cost_saved_usd: float


class Recommendation(BaseModel):
    action: Literal["markdown", "bundle", "donate", "adjust_order", "redistribute"]
    priority: int = Field(..., ge=1)
    description: str
    expected_impact: ActionImpact
    confidence: float = Field(..., ge=0.0, le=1.0)


class RecommendResponse(BaseModel):
    store_id: int
    product_id: int
    date: _dt.date
    recommendations: list[Recommendation]
    waste_risk_score: float
    waste_risk_tier: str


# ── Inventory ────────────────────────────────────────────────


class InventoryItem(BaseModel):
    product_id: int
    product_name: str
    category: str
    quantity_on_hand: int
    days_until_expiry: int | None
    waste_risk_score: float | None
    waste_risk_tier: str | None
    predicted_demand_today: float | None
    reorder_point: int


class InventoryResponse(BaseModel):
    store_id: int
    items: list[InventoryItem]
    total_items: int
    limit: int
    offset: int


class InventoryUpdateItem(BaseModel):
    product_id: int = Field(..., ge=1)
    actual_sold: int = Field(..., ge=0)
    actual_wasted: int = Field(0, ge=0)
    actual_donated: int = Field(0, ge=0)
    quantity_on_hand: int = Field(..., ge=0)


class InventoryUpdateRequest(BaseModel):
    store_id: int = Field(..., ge=1)
    date: _dt.date
    items: list[InventoryUpdateItem] = Field(..., min_length=1)


class ForecastAccuracyItem(BaseModel):
    predicted: float
    actual: int
    error_pct: float


class InventoryUpdateResponse(BaseModel):
    store_id: int
    date: _dt.date
    items_updated: int
    forecast_accuracy: dict[str, ForecastAccuracyItem]
    rolling_7d_mape: float | None


# ── Health ───────────────────────────────────────────────────


class HealthResponse(BaseModel):
    status: str
    timestamp: _dt.datetime


class ReadyResponse(BaseModel):
    status: str
    checks: dict[str, str]
    timestamp: _dt.datetime


# ── Errors ───────────────────────────────────────────────────


class ErrorResponse(BaseModel):
    detail: str
    error_code: str
    timestamp: _dt.datetime
