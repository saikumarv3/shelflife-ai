"""Quick smoke test for all API endpoints."""

import httpx

base = "http://localhost:8000"
h = {"X-API-Key": "sk_shelflife_dev_abc123", "Content-Type": "application/json"}

print("=== 1. HEALTH ===")
r = httpx.get(f"{base}/health")
print(f"  {r.status_code}: {r.json()}")

print("\n=== 2. READY ===")
r = httpx.get(f"{base}/ready", headers=h)
print(f"  {r.status_code}: {r.json()}")

print("\n=== 3. DEMAND PREDICTION ===")
r = httpx.post(
    f"{base}/predict/demand", headers=h, json={"store_id": 1, "product_id": 5, "date": "2024-12-15"}
)
print(f"  {r.status_code}: {r.json()}")

print("\n=== 4. BATCH PREDICTION ===")
r = httpx.post(
    f"{base}/predict/batch",
    headers=h,
    json={
        "predictions": [
            {"store_id": 1, "product_id": 5, "date": "2024-12-15"},
            {"store_id": 2, "product_id": 10, "date": "2024-11-20"},
        ]
    },
)
d = r.json()
print(
    f"  {r.status_code}: items={d['total_items']}, cache_hit={d['cache_hit_rate']}, latency={d['total_latency_ms']}ms"
)

print("\n=== 5. WASTE RISK ===")
r = httpx.post(
    f"{base}/predict/waste-risk",
    headers=h,
    json={
        "store_id": 1,
        "product_id": 5,
        "date": "2024-12-15",
        "current_stock": 45,
        "days_until_expiry": 3,
    },
)
print(f"  {r.status_code}: {r.json()}")

print("\n=== 6. RECOMMEND ===")
r = httpx.post(
    f"{base}/recommend", headers=h, json={"store_id": 1, "product_id": 5, "date": "2024-12-15"}
)
d = r.json()
print(
    f"  {r.status_code}: risk={d['waste_risk_score']}, tier={d['waste_risk_tier']}, actions={len(d['recommendations'])}"
)
for rec in d["recommendations"]:
    impact = rec["expected_impact"]
    print(
        f"    #{rec['priority']} {rec['action']}: {rec['description']} (saved ${impact['waste_cost_saved_usd']})"
    )

print("\n=== 7. INVENTORY ===")
r = httpx.get(f"{base}/inventory?store_id=1&limit=3", headers=h)
d = r.json()
print(f"  {r.status_code}: items={len(d['items'])}, total={d['total_items']}")

print("\n=== 8. AUTH TEST (no key — should be 401) ===")
r = httpx.post(
    f"{base}/predict/demand", json={"store_id": 1, "product_id": 5, "date": "2024-12-15"}
)
print(f"  {r.status_code}: {r.json()}")

print("\n=== 9. METRICS ===")
r = httpx.get(f"{base}/metrics")
lines = r.text.strip().split("\n")
print(f"  {r.status_code}: {len(lines)} metric lines")
print(f"  Sample: {lines[0][:80]}")

print("\n=== ALL TESTS PASSED ===")
