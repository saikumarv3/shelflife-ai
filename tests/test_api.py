"""API integration tests — endpoint status codes and response shapes."""


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


def test_ready(client, auth_headers):
    r = client.get("/ready", headers=auth_headers)
    assert r.status_code in (200, 503)
    body = r.json()
    assert "checks" in body
    assert "database" in body["checks"]


def test_auth_required(client):
    r = client.post("/predict/demand", json={
        "store_id": 1, "product_id": 1, "date": "2024-12-15",
    })
    assert r.status_code == 401


def test_predict_demand(client, auth_headers):
    r = client.post("/predict/demand", headers=auth_headers, json={
        "store_id": 1, "product_id": 1, "date": "2024-12-15",
    })
    assert r.status_code in (200, 404, 503)
    if r.status_code == 200:
        body = r.json()
        assert "predicted_demand" in body
        assert "confidence_lower" in body
        assert "model_version" in body


def test_predict_batch(client, auth_headers):
    r = client.post("/predict/batch", headers=auth_headers, json={
        "predictions": [
            {"store_id": 1, "product_id": 1, "date": "2024-12-15"},
            {"store_id": 1, "product_id": 2, "date": "2024-12-15"},
        ]
    })
    assert r.status_code in (200, 503)
    if r.status_code == 200:
        assert r.json()["total_items"] == 2


def test_predict_waste_risk(client, auth_headers):
    r = client.post("/predict/waste-risk", headers=auth_headers, json={
        "store_id": 1, "product_id": 1, "date": "2024-12-15",
        "current_stock": 45, "days_until_expiry": 3,
    })
    assert r.status_code in (200, 404, 503)
    if r.status_code == 200:
        body = r.json()
        assert "waste_risk_score" in body
        assert "waste_risk_tier" in body


def test_recommend(client, auth_headers):
    r = client.post("/recommend", headers=auth_headers, json={
        "store_id": 1, "product_id": 1, "date": "2024-12-15",
    })
    assert r.status_code in (200, 404, 503)


def test_inventory(client, auth_headers):
    r = client.get("/inventory?store_id=1&limit=5", headers=auth_headers)
    assert r.status_code in (200, 404)
    if r.status_code == 200:
        body = r.json()
        assert "items" in body
        assert body["limit"] == 5


def test_validation_error(client, auth_headers):
    r = client.post("/predict/demand", headers=auth_headers, json={
        "store_id": -1, "product_id": 1, "date": "2024-12-15",
    })
    assert r.status_code == 422


def test_metrics(client):
    r = client.get("/metrics")
    assert r.status_code == 200
    assert "shelflife_prediction" in r.text or "python_" in r.text
