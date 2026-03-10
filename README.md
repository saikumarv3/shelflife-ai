# ShelfLife AI

**AI-powered demand forecasting, waste risk prediction, and supply-chain recommendation engine for food retailers.**

ShelfLife AI is a production-style ML platform that helps grocery and food retailers reduce waste, optimize inventory, and improve profitability. It predicts daily demand, flags products at risk of expiring, and generates actionable recommendations (markdown, bundle, donate, adjust order, redistribute).

---

## Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Streamlit   │────▶│   FastAPI     │────▶│ PostgreSQL   │
│  Dashboard   │     │   REST API    │     │  (9 tables)  │
│  :8501       │     │   :8000       │     │  :5432       │
└──────────────┘     └──────┬───────┘     └──────────────┘
                            │
                     ┌──────┴───────┐
                     │              │
              ┌──────▼──┐   ┌──────▼───┐
              │  Redis   │   │  MLflow   │
              │  Cache   │   │  Registry │
              │  :6379   │   │  :5001    │
              └─────────┘   └──────────┘
```

**ML Pipeline:**

```
Raw Data → Feature Engineering (35+ features) → Train/Val/Test Split
  ├── Demand Forecaster  (XGBoost + LightGBM ensemble, quantile regression)
  └── Waste Risk Classifier (XGBoost, class-imbalance aware)
      ↓
Recommendation Engine → Rule-based triggers + ML-scored ranking
      ↓
Monitoring → Prometheus metrics, drift detection (PSI/KS), auto-retraining
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.12 |
| Package Manager | uv (Hatchling) |
| API | FastAPI, Uvicorn, Pydantic v2 |
| ML Models | XGBoost, LightGBM, scikit-learn |
| Experiment Tracking | MLflow |
| Database | PostgreSQL 16 |
| Caching | Redis 7 |
| Dashboard | Streamlit, Plotly |
| Monitoring | Prometheus client, custom metrics |
| Scheduling | APScheduler (cron jobs) |
| Containerization | Docker, Docker Compose |
| CI/CD | GitHub Actions |
| Linting | Ruff |

---

## Quick Start

### Prerequisites

- Python 3.12+, [uv](https://docs.astral.sh/uv/), Docker Desktop

### Option 1: Local Development

```bash
# Clone and install
git clone <repo-url> && cd shelflife-ai
uv sync

# Start infrastructure
docker compose up -d postgres redis mlflow

# Seed database with synthetic data (54,900 records)
uv run python -m db.seed

# Build features and train models
uv run python -m mlops.train_pipeline

# Start the API
uv run uvicorn api.main:app --reload --port 8000

# Start the dashboard (new terminal)
uv run streamlit run dashboard/app.py
```

### Option 2: Full Docker Stack

```bash
docker compose up --build
```

Open:
- API Swagger: http://localhost:8000/docs
- Dashboard: http://localhost:8501
- MLflow UI: http://localhost:5001

---

## API Endpoints

| Method | Endpoint | Description |
|--------|---------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/ready` | Readiness (DB, Redis, models) |
| `GET` | `/metrics` | Prometheus metrics |
| `POST` | `/predict/demand` | Single demand forecast |
| `POST` | `/predict/batch` | Batch demand forecast |
| `POST` | `/predict/waste-risk` | Waste risk score + tier |
| `POST` | `/recommend` | ML-ranked recommendations |
| `GET` | `/inventory` | Inventory snapshots (paginated) |
| `POST` | `/inventory/update` | Record actuals (feedback loop) |

All prediction endpoints require `X-API-Key` header.

---

## Dashboard Pages

| Page | Shows |
|------|-------|
| **Demand Forecast** | Actual vs predicted demand charts, MAPE metrics, top products |
| **Waste Risk** | Waste by category, daily waste trend, at-risk items |
| **Recommendations** | Action types breakdown, acceptance rate, savings |
| **Model Performance** | Alerts, feature store stats, drift status, promotion history |

---

## MLOps Features

- **Experiment Tracking**: MLflow logs every training run with params, metrics, artifacts
- **Model Registry**: Versioned models with local joblib fallback
- **Drift Detection**: PSI + Kolmogorov-Smirnov tests on critical features
- **Auto-Retraining**: Scheduled (weekly) + triggered (drift/MAPE threshold)
- **Validation Gate**: New model must outperform production model before promotion
- **Feedback Loop**: Records predictions vs actuals, computes rolling MAPE
- **Prometheus Metrics**: Request counts, latency, cache hits, MAPE, drift PSI

### Scheduled Jobs (APScheduler)

| Job | Schedule | Description |
|-----|----------|-------------|
| Daily Forecast | 6:00 AM daily | Batch predict for all store-product pairs |
| Drift Check | 11:00 PM daily | PSI + KS test on critical features |
| Feedback | 11:30 PM daily | Compute rolling MAPE per store |
| Retrain | 2:00 AM Sunday | Full retraining with validation gate |

---

## Running Tests

```bash
uv run pytest tests/ -v --tb=short
```

Test suites:
- `test_data_quality.py` — Schema validation, null checks, FK integrity
- `test_features.py` — Feature pipeline correctness (35 columns, no NaN)
- `test_models.py` — Model training, predictions, baselines
- `test_api.py` — Endpoint integration (status codes, auth, response shapes)

---

## Manual MLOps Commands

```bash
# Run drift check
uv run python -m scripts.run_drift_check

# Force retraining
uv run python -m scripts.run_retrain --force

# Run daily forecast
uv run python -m scripts.run_daily_forecast

# Compute feedback MAPE
uv run python -m scripts.run_feedback
```

---

## Project Structure

```
shelflife-ai/
├── api/                    # FastAPI application
│   ├── main.py             # App factory + lifespan + scheduler
│   ├── schemas.py          # Pydantic request/response models
│   ├── middleware.py        # Auth, rate limiting, logging
│   ├── dependencies.py     # DI: DB, Redis, ModelManager
│   └── routes/             # Endpoint modules
│       ├── health.py       # /health, /ready, /metrics
│       ├── forecast.py     # /predict/demand, /predict/batch
│       ├── waste.py        # /predict/waste-risk
│       ├── recommend.py    # /recommend
│       └── inventory.py    # /inventory, /inventory/update
├── config/                 # Centralized settings (pydantic-settings)
├── dashboard/              # Streamlit 4-page dashboard
├── data_generator/         # Synthetic data generation
├── db/                     # SQLAlchemy models + session + seed
├── docs/                   # Architecture & design documents
├── features/               # Feature engineering + feature store
├── mlops/                  # Train pipeline, registry, drift, retrain
├── models/                 # Demand forecaster, waste risk, evaluation
├── monitoring/             # Prometheus metrics + feedback loop
├── recommendation/         # Rule engine + action definitions
├── scripts/                # Standalone MLOps job scripts
├── tests/                  # Pytest test suites
├── .github/workflows/      # CI/CD pipeline
├── docker-compose.yml      # 5-service stack
├── Dockerfile              # API multi-stage build
├── Dockerfile.dashboard    # Dashboard multi-stage build
└── pyproject.toml          # Dependencies (uv / Hatchling)
```
