"""Prometheus metrics for ShelfLife AI API."""

from prometheus_client import Counter, Gauge, Histogram

# ── Request metrics ──────────────────────────────────────────

PREDICTION_REQUESTS = Counter(
    "shelflife_prediction_requests_total",
    "Total prediction requests",
    ["endpoint", "status"],
)

PREDICTION_LATENCY = Histogram(
    "shelflife_prediction_latency_seconds",
    "Prediction request latency",
    ["endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5),
)

# ── Cache metrics ────────────────────────────────────────────

CACHE_HITS = Counter("shelflife_cache_hits_total", "Redis cache hits")
CACHE_MISSES = Counter("shelflife_cache_misses_total", "Redis cache misses")

# ── Forecast quality metrics ─────────────────────────────────

FORECAST_ERROR = Histogram(
    "shelflife_forecast_error_absolute",
    "Absolute forecast error per prediction",
    ["store_id"],
    buckets=(0.5, 1, 2, 5, 10, 20, 50, 100),
)

FORECAST_MAPE_7D = Gauge(
    "shelflife_forecast_mape_7d_rolling",
    "Rolling 7-day MAPE per store",
    ["store_id"],
)

# ── Model metrics ────────────────────────────────────────────

MODEL_VERSION = Gauge(
    "shelflife_model_version_info",
    "Current model version (1 = loaded)",
    ["model_name", "version"],
)

# ── Business metrics ─────────────────────────────────────────

WASTE_PREVENTED_KG = Counter(
    "shelflife_waste_prevented_kg_total",
    "Estimated kg of waste prevented",
)

RECOMMENDATIONS_GENERATED = Counter(
    "shelflife_recommendations_total",
    "Total recommendations generated",
    ["action_type"],
)

RECOMMENDATIONS_ACCEPTED = Counter(
    "shelflife_recommendations_accepted_total",
    "Total recommendations accepted by users",
    ["action_type"],
)

# ── Drift metrics ────────────────────────────────────────────

DRIFT_PSI = Gauge(
    "shelflife_drift_psi",
    "Population Stability Index per feature",
    ["feature"],
)

DRIFT_ALERT = Counter(
    "shelflife_drift_alerts_total",
    "Number of drift alerts fired",
)

RETRAIN_RUNS = Counter(
    "shelflife_retrain_runs_total",
    "Total retraining runs",
    ["outcome"],
)
