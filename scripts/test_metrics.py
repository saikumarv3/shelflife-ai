"""Test metrics: make a few requests then check /metrics for Prometheus data."""

import httpx

base = "http://localhost:8000"
h = {"X-API-Key": "sk_shelflife_dev_abc123", "Content-Type": "application/json"}

# Make some requests to generate metrics
for i in range(3):
    httpx.post(f"{base}/predict/demand", headers=h, json={
        "store_id": 1, "product_id": i + 1, "date": "2024-12-15",
    })

httpx.post(f"{base}/predict/waste-risk", headers=h, json={
    "store_id": 1, "product_id": 5, "date": "2024-12-15",
    "current_stock": 45, "days_until_expiry": 3,
})

httpx.post(f"{base}/recommend", headers=h, json={
    "store_id": 1, "product_id": 5, "date": "2024-12-15",
})

# Now check metrics
r = httpx.get(f"{base}/metrics")
lines = r.text.strip().split("\n")

print(f"Total metric lines: {len(lines)}")
print()

interesting = [
    "shelflife_prediction_requests",
    "shelflife_prediction_latency",
    "shelflife_cache_hits",
    "shelflife_cache_misses",
    "shelflife_model_version",
    "shelflife_recommendations",
]

for keyword in interesting:
    matches = [l for l in lines if keyword in l and not l.startswith("#")]
    if matches:
        print(f"--- {keyword} ---")
        for m in matches[:5]:
            print(f"  {m}")
        print()
