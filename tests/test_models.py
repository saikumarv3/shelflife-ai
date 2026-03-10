"""Tests for ML models — training, prediction, and evaluation."""

import numpy as np

from models.demand_forecast import DemandForecaster
from models.waste_risk import WasteRiskClassifier
from models.evaluation import mape, evaluate_forecast, compute_baselines


def test_demand_forecaster_trains_and_predicts():
    np.random.seed(42)
    X = np.random.randn(200, 10).astype(np.float32)
    y = (X[:, 0] * 5 + 10 + np.random.randn(200)).astype(np.float32)

    model = DemandForecaster()
    result = model.train(X[:150], y[:150], X[150:], y[150:])
    assert result["status"] == "trained"

    preds = model.predict(X[150:])
    assert len(preds) == 50
    assert all(preds >= 0)


def test_demand_confidence_intervals():
    np.random.seed(42)
    X = np.random.randn(200, 10).astype(np.float32)
    y = (X[:, 0] * 5 + 10 + np.random.randn(200)).astype(np.float32)

    model = DemandForecaster()
    model.train(X[:150], y[:150])

    result = model.predict_with_intervals(X[150:])
    assert "predicted_demand" in result
    assert "confidence_lower" in result
    assert "confidence_upper" in result
    assert all(result["confidence_lower"] <= result["confidence_upper"])


def test_waste_risk_classifier():
    np.random.seed(42)
    X = np.random.randn(200, 10).astype(np.float32)
    y = (X[:, 0] > 0).astype(int)

    model = WasteRiskClassifier()
    info = model.train(X[:150], y[:150], X[150:], y[150:])
    assert info["status"] == "trained"

    proba = model.predict_proba(X[150:])
    assert len(proba) == 50
    assert all(0 <= p <= 1 for p in proba)

    tiers = model.predict_tier(X[150:])
    assert all(t in ("low", "medium", "high", "critical") for t in tiers)


def test_mape_excludes_zeros():
    y_true = np.array([10.0, 0.0, 20.0])
    y_pred = np.array([12.0, 5.0, 18.0])
    result = mape(y_true, y_pred)
    assert 0 < result < 1


def test_baselines():
    y_true = np.array([10.0, 15.0, 20.0, 25.0])
    y_lag1 = np.array([12.0, 14.0, 18.0, 22.0])
    y_lag7 = np.array([11.0, 16.0, 19.0, 24.0])
    result = compute_baselines(y_true, y_lag1, y_lag7)
    assert "naive_lag1_mape" in result
    assert "naive_lag7_mape" in result
