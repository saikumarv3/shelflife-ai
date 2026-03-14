"""
Evaluation framework — ML metrics, business cost metric, and baseline comparisons.
"""

from __future__ import annotations

import numpy as np
from sklearn.metrics import (
    average_precision_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
)

# ── Demand forecast metrics ──────────────────────────────────


def mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Mean Absolute Percentage Error. Excludes zeros in y_true."""
    mask = y_true > 0
    if mask.sum() == 0:
        return 0.0
    return float(np.mean(np.abs(y_true[mask] - y_pred[mask]) / y_true[mask]))


def wape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Weighted Absolute Percentage Error."""
    total = y_true.sum()
    if total == 0:
        return 0.0
    return float(np.sum(np.abs(y_true - y_pred)) / total)


def business_cost_metric(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    unit_price: np.ndarray,
    cost_price: np.ndarray,
) -> float:
    """
    Asymmetric cost: overforecast causes waste (cost_price per unit),
    underforecast causes lost margin (margin per unit).
    """
    error = y_pred - y_true
    margin = unit_price - cost_price

    overforecast_cost = np.where(error > 0, error * cost_price, 0)
    underforecast_cost = np.where(error < 0, -error * margin, 0)

    return float(overforecast_cost.sum() + underforecast_cost.sum())


def evaluate_forecast(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    unit_price: np.ndarray | None = None,
    cost_price: np.ndarray | None = None,
) -> dict[str, float]:
    """Compute all demand forecast metrics."""
    metrics = {
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "mape": mape(y_true, y_pred),
        "wape": wape(y_true, y_pred),
        "r2": float(r2_score(y_true, y_pred)),
    }
    if unit_price is not None and cost_price is not None:
        metrics["business_cost"] = business_cost_metric(y_true, y_pred, unit_price, cost_price)
    return metrics


# ── Waste risk metrics ───────────────────────────────────────


def evaluate_waste_risk(y_true: np.ndarray, y_proba: np.ndarray, threshold: float = 0.5) -> dict[str, float]:
    """Compute all waste risk classification metrics."""
    y_pred = (y_proba >= threshold).astype(int)
    return {
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "auc_roc": float(roc_auc_score(y_true, y_proba)) if len(np.unique(y_true)) > 1 else 0.0,
        "auc_pr": float(average_precision_score(y_true, y_proba)) if len(np.unique(y_true)) > 1 else 0.0,
    }


# ── Baseline models ──────────────────────────────────────────


def compute_baselines(y_true: np.ndarray, y_lag1: np.ndarray, y_lag7: np.ndarray) -> dict[str, float]:
    """Compute MAPE for naive baselines."""
    baselines = {}

    mask1 = ~np.isnan(y_lag1) & (y_true > 0)
    if mask1.sum() > 0:
        baselines["naive_lag1_mape"] = mape(y_true[mask1], y_lag1[mask1])

    mask7 = ~np.isnan(y_lag7) & (y_true > 0)
    if mask7.sum() > 0:
        baselines["naive_lag7_mape"] = mape(y_true[mask7], y_lag7[mask7])

    if mask7.sum() > 0:
        avg7 = np.nanmean(np.column_stack([y_lag1, y_lag7]), axis=1)
        mask_avg = ~np.isnan(avg7) & (y_true > 0)
        if mask_avg.sum() > 0:
            baselines["moving_avg_mape"] = mape(y_true[mask_avg], avg7[mask_avg])

    return baselines
