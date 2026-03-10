"""Drift detection: Population Stability Index and Kolmogorov-Smirnov test.

Compares training-time feature distributions to recent inference data.
Fires alerts if PSI > threshold or KS test rejects null hypothesis.
"""

from __future__ import annotations

import json
import logging
from datetime import date, timedelta

import numpy as np
from scipy.stats import ks_2samp
from sqlalchemy import text
from sqlalchemy.engine import Engine

from config.settings import settings
from monitoring.metrics import DRIFT_PSI, DRIFT_ALERT

logger = logging.getLogger(__name__)

CRITICAL_FEATURES = [
    "sales_lag_1d", "sales_lag_7d", "sales_rolling_7d_mean",
    "sales_rolling_28d_mean", "waste_rolling_7d_rate",
    "stock_to_sales_ratio", "temperature_avg", "promotion_discount",
]


def calculate_psi(expected: np.ndarray, actual: np.ndarray, bins: int = 10) -> float:
    """Population Stability Index between two distributions.

    PSI < 0.1  => no shift
    PSI 0.1-0.2 => moderate shift
    PSI > 0.2  => significant shift
    """
    eps = 1e-4
    min_val = min(expected.min(), actual.min())
    max_val = max(expected.max(), actual.max())

    if max_val == min_val:
        return 0.0

    breakpoints = np.linspace(min_val, max_val, bins + 1)

    expected_pct = np.histogram(expected, bins=breakpoints)[0] / len(expected) + eps
    actual_pct = np.histogram(actual, bins=breakpoints)[0] / len(actual) + eps

    psi = np.sum((actual_pct - expected_pct) * np.log(actual_pct / expected_pct))
    return float(psi)


def check_ks_test(
    training_dist: np.ndarray,
    recent_dist: np.ndarray,
    alpha: float = 0.05,
) -> dict:
    """Kolmogorov-Smirnov two-sample test."""
    stat, p_value = ks_2samp(training_dist, recent_dist)
    return {
        "ks_statistic": round(float(stat), 4),
        "p_value": round(float(p_value), 4),
        "drifted": p_value < alpha,
    }


def run_drift_check(
    engine: Engine,
    recent_days: int = 7,
    psi_threshold: float | None = None,
) -> dict[str, dict]:
    """Check all critical features for drift. Returns per-feature results."""
    threshold = psi_threshold or settings.drift_psi_threshold
    recent_start = date.today() - timedelta(days=recent_days)
    train_cutoff = "2024-10-01"

    results: dict[str, dict] = {}
    any_drifted = False

    with engine.connect() as conn:
        for feature in CRITICAL_FEATURES:
            train_rows = conn.execute(
                text(
                    f"SELECT {feature} FROM feature_store "
                    f"WHERE date < :cutoff AND {feature} IS NOT NULL"
                ),
                {"cutoff": train_cutoff},
            ).scalars().all()

            recent_rows = conn.execute(
                text(
                    f"SELECT {feature} FROM feature_store "
                    f"WHERE date >= :start_dt AND {feature} IS NOT NULL"
                ),
                {"start_dt": recent_start},
            ).scalars().all()

            if len(train_rows) < 10 or len(recent_rows) < 10:
                results[feature] = {
                    "psi": 0.0, "drifted": False, "reason": "insufficient_data",
                }
                continue

            train_arr = np.array(train_rows, dtype=float)
            recent_arr = np.array(recent_rows, dtype=float)

            psi = calculate_psi(train_arr, recent_arr)
            ks = check_ks_test(train_arr, recent_arr)
            drifted = psi > threshold or ks["drifted"]

            results[feature] = {
                "psi": round(psi, 4),
                "ks_statistic": ks["ks_statistic"],
                "ks_p_value": ks["p_value"],
                "drifted": drifted,
            }

            DRIFT_PSI.labels(feature=feature).set(psi)

            if drifted:
                any_drifted = True
                logger.warning(
                    "DRIFT DETECTED: %s  PSI=%.4f, KS p=%.4f",
                    feature, psi, ks["p_value"],
                )

    if any_drifted:
        DRIFT_ALERT.inc()
        _insert_drift_alert(engine, results)

    return results


def _insert_drift_alert(engine: Engine, results: dict) -> None:
    """Insert a drift alert into the alerts table."""
    drifted = {f: r for f, r in results.items() if r.get("drifted")}
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO alerts (alert_type, severity, message, metadata_json)
                VALUES ('data_drift', :sev, :msg, :meta)
            """),
            {
                "sev": "high" if len(drifted) > 2 else "medium",
                "msg": (
                    f"Data drift detected in {len(drifted)} feature(s): "
                    f"{', '.join(drifted.keys())}"
                ),
                "meta": json.dumps({k: v for k, v in drifted.items()}),
            },
        )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    from db.session import engine

    logger.info(
        "Running drift detection on %d critical features...",
        len(CRITICAL_FEATURES),
    )
    results = run_drift_check(engine)

    print()
    print("=" * 50)
    print("  DRIFT DETECTION RESULTS")
    print("=" * 50)
    for feat, info in results.items():
        status = "DRIFT" if info["drifted"] else "OK"
        psi = info["psi"]
        print(f"  {feat:30s}  PSI={psi:.4f}  [{status}]")
    print("=" * 50)
