"""Test with a high-risk product scenario."""

import httpx

h = {"X-API-Key": "sk_shelflife_dev_abc123", "Content-Type": "application/json"}

r = httpx.post(
    "http://localhost:8000/predict/waste-risk",
    headers=h,
    json={
        "store_id": 2,
        "product_id": 3,
        "date": "2024-10-15",
        "current_stock": 80,
        "days_until_expiry": 1,
    },
)
print("WASTE RISK:", r.json())

print()
r = httpx.post(
    "http://localhost:8000/recommend",
    headers=h,
    json={
        "store_id": 2,
        "product_id": 3,
        "date": "2024-10-15",
    },
)
d = r.json()
risk = d["waste_risk_score"]
tier = d["waste_risk_tier"]
count = len(d["recommendations"])
print(f"RECOMMEND: risk={risk}, tier={tier}, actions={count}")
for rec in d["recommendations"]:
    impact = rec["expected_impact"]
    print(f"  #{rec['priority']} {rec['action']}: {rec['description']}")
    print(f"     saved=${impact['waste_cost_saved_usd']}, waste_reduction={impact['waste_reduction_units']} units")
