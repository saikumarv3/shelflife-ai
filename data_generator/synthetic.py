"""
Synthetic data generator for ShelfLife AI.

Produces realistic grocery retail data: stores, categories, products,
daily sales (with seasonality, promotions, holidays), inventory snapshots,
and temperature data for one calendar year.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, timedelta

import numpy as np
import pandas as pd

from config.settings import settings

# ── Seed ──────────────────────────────────────────────────────
RNG = np.random.default_rng(settings.random_seed)

# ── Holiday calendar ──────────────────────────────────────────
US_HOLIDAYS_2024 = {
    date(2024, 1, 1),    # New Year's Day
    date(2024, 1, 15),   # MLK Day
    date(2024, 2, 14),   # Valentine's Day
    date(2024, 3, 17),   # St Patrick's Day
    date(2024, 5, 27),   # Memorial Day
    date(2024, 7, 4),    # Independence Day
    date(2024, 9, 2),    # Labor Day
    date(2024, 10, 31),  # Halloween
    date(2024, 11, 28),  # Thanksgiving
    date(2024, 12, 24),  # Christmas Eve
    date(2024, 12, 25),  # Christmas Day
    date(2024, 12, 31),  # New Year's Eve
}


# ── Output containers ────────────────────────────────────────

@dataclass
class SyntheticData:
    stores: list[dict] = field(default_factory=list)
    categories: list[dict] = field(default_factory=list)
    products: list[dict] = field(default_factory=list)
    sales: list[dict] = field(default_factory=list)
    inventory: list[dict] = field(default_factory=list)


# ── Store definitions ────────────────────────────────────────

STORE_DEFS = [
    {"name": "Metro Downtown #12", "location": "Chicago, IL", "size_sqft": 42000, "type": "urban"},
    {"name": "FreshMart Plano #7", "location": "Dallas, TX", "size_sqft": 55000, "type": "suburban"},
    {"name": "Green Valley Market", "location": "Burlington, VT", "size_sqft": 18000, "type": "rural"},
]

# ── Category definitions ─────────────────────────────────────

CATEGORY_DEFS = [
    {"name": "Dairy",          "perishability": "high",   "avg_shelf_days": 14},
    {"name": "Bakery",         "perishability": "high",   "avg_shelf_days": 5},
    {"name": "Produce",        "perishability": "high",   "avg_shelf_days": 7},
    {"name": "Deli/Prepared",  "perishability": "high",   "avg_shelf_days": 3},
    {"name": "Meat & Seafood", "perishability": "high",   "avg_shelf_days": 5},
    {"name": "Frozen",         "perishability": "low",    "avg_shelf_days": 180},
    {"name": "Beverages",      "perishability": "low",    "avg_shelf_days": 90},
    {"name": "Snacks & Dry",   "perishability": "low",    "avg_shelf_days": 365},
]

# ── Product catalog ──────────────────────────────────────────
# (name, category_index, unit_price, cost_price, shelf_life_days, storage_temp)

PRODUCT_DEFS = [
    # Dairy (0) — 7 products
    ("Whole Milk 1 Gal", 0, 4.29, 2.80, 14, "cold"),
    ("2% Milk 1 Gal", 0, 4.19, 2.70, 14, "cold"),
    ("Greek Yogurt 32oz", 0, 5.99, 3.20, 21, "cold"),
    ("Cheddar Cheese Block", 0, 6.49, 3.50, 30, "cold"),
    ("Butter Unsalted 1lb", 0, 4.99, 2.90, 60, "cold"),
    ("Heavy Cream 1pt", 0, 3.99, 2.10, 14, "cold"),
    ("Cottage Cheese 16oz", 0, 3.49, 1.80, 14, "cold"),
    # Bakery (1) — 7 products
    ("Sourdough Loaf", 1, 5.49, 2.20, 5, "ambient"),
    ("Whole Wheat Bread", 1, 4.29, 1.80, 5, "ambient"),
    ("Croissants 4-pack", 1, 5.99, 2.50, 3, "ambient"),
    ("Bagels 6-pack", 1, 4.49, 1.90, 5, "ambient"),
    ("Dinner Rolls 12-pack", 1, 3.99, 1.60, 4, "ambient"),
    ("Blueberry Muffins 4pk", 1, 6.49, 2.80, 3, "ambient"),
    ("Ciabatta Rolls 4pk", 1, 4.99, 2.00, 4, "ambient"),
    # Produce (2) — 7 products
    ("Organic Bananas 1lb", 2, 0.79, 0.35, 7, "ambient"),
    ("Strawberries 1lb", 2, 4.99, 2.50, 5, "cold"),
    ("Avocados Each", 2, 1.99, 0.90, 5, "ambient"),
    ("Baby Spinach 5oz", 2, 3.99, 1.80, 7, "cold"),
    ("Roma Tomatoes 1lb", 2, 2.49, 1.10, 7, "ambient"),
    ("Blueberries 6oz", 2, 4.49, 2.20, 7, "cold"),
    ("Green Bell Pepper Each", 2, 1.29, 0.55, 10, "cold"),
    # Deli/Prepared (3) — 6 products
    ("Rotisserie Chicken", 3, 8.99, 4.50, 3, "cold"),
    ("Caesar Salad Kit", 3, 7.49, 3.20, 3, "cold"),
    ("Turkey Deli Slices 8oz", 3, 5.99, 3.00, 5, "cold"),
    ("Hummus 10oz", 3, 4.99, 2.20, 7, "cold"),
    ("Fresh Sushi 8pc", 3, 9.99, 5.50, 2, "cold"),
    ("Pasta Salad 1lb", 3, 6.49, 3.10, 3, "cold"),
    # Meat & Seafood (4) — 6 products
    ("Atlantic Salmon 1lb", 4, 12.99, 8.50, 5, "cold"),
    ("Ground Beef 85% 1lb", 4, 6.99, 4.20, 5, "cold"),
    ("Chicken Breast 1lb", 4, 5.49, 3.00, 5, "cold"),
    ("Pork Chops 1lb", 4, 7.49, 4.00, 5, "cold"),
    ("Shrimp 1lb Frozen", 4, 10.99, 6.50, 7, "cold"),
    ("Italian Sausage 4-pack", 4, 6.49, 3.50, 7, "cold"),
    # Frozen (5) — 6 products
    ("Frozen Pizza Pepperoni", 5, 7.99, 3.80, 180, "frozen"),
    ("Frozen Vegetables Medley", 5, 3.49, 1.50, 240, "frozen"),
    ("Ice Cream Vanilla 1pt", 5, 5.99, 2.80, 180, "frozen"),
    ("Frozen Waffles 10ct", 5, 4.29, 1.90, 180, "frozen"),
    ("Chicken Nuggets 2lb", 5, 8.49, 4.00, 180, "frozen"),
    ("Frozen Burritos 8pk", 5, 6.99, 3.20, 180, "frozen"),
    # Beverages (6) — 6 products
    ("Orange Juice 64oz", 6, 4.49, 2.20, 21, "cold"),
    ("Spring Water 24pk", 6, 4.99, 1.80, 365, "ambient"),
    ("Cola 12pk Cans", 6, 6.99, 3.50, 180, "ambient"),
    ("Almond Milk 64oz", 6, 3.99, 1.90, 30, "cold"),
    ("Kombucha Ginger 16oz", 6, 3.49, 1.60, 60, "cold"),
    ("Cold Brew Coffee 32oz", 6, 5.99, 2.80, 14, "cold"),
    # Snacks & Dry (7) — 5 products
    ("Tortilla Chips 13oz", 7, 4.49, 1.80, 180, "ambient"),
    ("Granola Bars 12ct", 7, 5.99, 2.80, 365, "ambient"),
    ("Trail Mix 16oz", 7, 7.49, 3.50, 180, "ambient"),
    ("Peanut Butter 16oz", 7, 4.29, 2.00, 365, "ambient"),
    ("Pasta Penne 1lb", 7, 2.49, 0.90, 730, "ambient"),
]
assert len(PRODUCT_DEFS) == 50

# ── Store size multipliers (urban=high traffic, rural=low) ───

STORE_DEMAND_MULT = {"urban": 1.3, "suburban": 1.0, "rural": 0.6}

# ── Weekday multipliers per category index ───────────────────
# index 0=Mon … 6=Sun

WEEKDAY_MULTS: dict[int, list[float]] = {
    0: [0.9, 0.9, 1.0, 1.0, 1.1, 1.2, 1.1],   # Dairy
    1: [0.8, 0.8, 0.9, 0.9, 1.1, 1.3, 1.3],   # Bakery (weekend peak)
    2: [0.9, 0.9, 1.0, 1.0, 1.1, 1.2, 1.1],   # Produce
    3: [1.0, 1.0, 1.0, 1.1, 1.2, 1.1, 0.8],   # Deli (weekday lunch)
    4: [0.8, 0.9, 0.9, 1.0, 1.2, 1.3, 1.0],   # Meat (Fri-Sat grill)
    5: [0.9, 0.9, 1.0, 1.0, 1.0, 1.1, 1.1],   # Frozen
    6: [1.0, 1.0, 1.0, 1.0, 1.0, 1.1, 1.0],   # Beverages
    7: [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0],   # Snacks (flat)
}

# Seasonal phase shifts: 0=peak in summer, π=peak in winter
SEASONAL_PHASE: dict[int, float] = {
    0: 0.0,           # Dairy: flat
    1: 0.0,           # Bakery: flat
    2: 0.0,           # Produce: summer peak
    3: 0.0,           # Deli: summer peak
    4: 0.0,           # Meat: summer peak (grilling)
    5: math.pi,       # Frozen: winter peak (comfort food)
    6: 0.0,           # Beverages: summer peak
    7: math.pi,       # Snacks: winter peak (indoor snacking)
}

SEASONAL_AMPLITUDE: dict[int, float] = {
    0: 0.05, 1: 0.05, 2: 0.15, 3: 0.10, 4: 0.15, 5: 0.10, 6: 0.20, 7: 0.08,
}

# Category-level waste rate (fraction of overstock that becomes waste)
CATEGORY_WASTE_RATE: dict[int, float] = {
    0: 0.08, 1: 0.12, 2: 0.10, 3: 0.15, 4: 0.10, 5: 0.02, 6: 0.03, 7: 0.01,
}

# Base daily demand per product (units/day at a suburban store)
BASE_DEMAND = [
    # Dairy
    80, 60, 45, 30, 25, 20, 18,
    # Bakery
    50, 40, 25, 35, 30, 20, 22,
    # Produce
    120, 35, 40, 30, 50, 25, 35,
    # Deli
    30, 20, 25, 18, 12, 15,
    # Meat
    20, 35, 40, 18, 15, 22,
    # Frozen
    18, 25, 22, 20, 15, 12,
    # Beverages
    30, 45, 35, 20, 12, 15,
    # Snacks
    20, 25, 15, 22, 30,
]
assert len(BASE_DEMAND) == 50

# City temperature profiles (base °F, amplitude °F)
CITY_TEMPS = {
    "Chicago, IL":     (50.0, 25.0),
    "Dallas, TX":      (65.0, 20.0),
    "Burlington, VT":  (45.0, 28.0),
}


def _date_range(start: str, end: str) -> list[date]:
    s = date.fromisoformat(start)
    e = date.fromisoformat(end)
    return [s + timedelta(days=i) for i in range((e - s).days + 1)]


def _temperature(d: date, city: str) -> float:
    base, amp = CITY_TEMPS[city]
    day_of_year = d.timetuple().tm_yday
    seasonal = amp * math.sin(2 * math.pi * (day_of_year - 80) / 365)
    noise = RNG.normal(0, 3)
    return round(base + seasonal + noise, 1)


def generate_all() -> SyntheticData:
    """Generate all synthetic data and return as a SyntheticData object."""
    data = SyntheticData()
    dates = _date_range(settings.data_start_date, settings.data_end_date)

    # ── Stores ────────────────────────────────────────────
    for i, sd in enumerate(STORE_DEFS, start=1):
        data.stores.append({"store_id": i, **sd})

    # ── Categories ────────────────────────────────────────
    for i, cd in enumerate(CATEGORY_DEFS, start=1):
        data.categories.append({"category_id": i, **cd})

    # ── Products ──────────────────────────────────────────
    for i, (name, cat_idx, price, cost, shelf, temp) in enumerate(PRODUCT_DEFS, start=1):
        data.products.append({
            "product_id": i,
            "category_id": cat_idx + 1,
            "name": name,
            "unit_price": price,
            "cost_price": cost,
            "shelf_life_days": shelf,
            "storage_temp": temp,
        })

    # ── Sales + Inventory per store × product × date ─────
    for store in data.stores:
        store_id = store["store_id"]
        store_mult = STORE_DEMAND_MULT[store["type"]]
        city = store["location"]

        for prod in data.products:
            pid = prod["product_id"]
            cat_idx = prod["category_id"] - 1
            base = BASE_DEMAND[pid - 1]
            shelf_days = prod["shelf_life_days"]
            price = prod["unit_price"]
            cost = prod["cost_price"]

            stock = int(base * store_mult * 3)
            last_delivery = dates[0]
            reorder_freq = max(2, shelf_days // 3)
            reorder_point = int(base * store_mult * 1.5)
            safety_stock = int(base * store_mult * 0.5)

            promo_days = set()
            num_promo_bursts = RNG.integers(3, 8)
            for _ in range(num_promo_bursts):
                burst_start = RNG.integers(0, len(dates) - 4)
                burst_len = RNG.integers(2, 5)
                for j in range(burst_len):
                    if burst_start + j < len(dates):
                        promo_days.add(burst_start + j)

            trend_slope = RNG.uniform(-0.0003, 0.0005)

            for day_idx, d in enumerate(dates):
                day_of_week = d.weekday()
                day_of_year = d.timetuple().tm_yday
                is_holiday = d in US_HOLIDAYS_2024
                is_promo = day_idx in promo_days
                promo_discount = round(RNG.uniform(0.10, 0.35), 2) if is_promo else 0.0

                weekday_mult = WEEKDAY_MULTS[cat_idx][day_of_week]
                phase = SEASONAL_PHASE[cat_idx]
                amp = SEASONAL_AMPLITUDE[cat_idx]
                seasonal_mult = 1.0 + amp * math.sin(2 * math.pi * (day_of_year - 80) / 365 + phase)
                holiday_mult = RNG.uniform(1.3, 1.5) if is_holiday else 1.0
                promo_mult = 1.0 + promo_discount * RNG.uniform(1.5, 3.0) if is_promo else 1.0
                trend_mult = 1.0 + trend_slope * day_idx

                temp = _temperature(d, city)
                if cat_idx in (5,):  # frozen: sells more when hot
                    temp_mult = 1.0 + max(0, (temp - 70)) * 0.005
                elif cat_idx in (6,):  # beverages: sells more when hot
                    temp_mult = 1.0 + max(0, (temp - 65)) * 0.008
                elif cat_idx in (2, 4):  # produce, meat: mild summer boost
                    temp_mult = 1.0 + max(0, (temp - 60)) * 0.003
                else:
                    temp_mult = 1.0

                raw_demand = (
                    base
                    * store_mult
                    * weekday_mult
                    * seasonal_mult
                    * holiday_mult
                    * promo_mult
                    * temp_mult
                    * trend_mult
                )
                noise_sigma = raw_demand * RNG.uniform(0.08, 0.15)
                demand = max(0, int(round(raw_demand + RNG.normal(0, noise_sigma))))

                sold = min(demand, stock)
                overstock = max(0, stock - sold)
                waste_rate = CATEGORY_WASTE_RATE[cat_idx]
                expiry_factor = min(1.0, 3.0 / max(shelf_days, 1))
                waste_prob = waste_rate * expiry_factor
                wasted = int(overstock * waste_prob * RNG.uniform(0.3, 1.5)) if overstock > 0 else 0
                wasted = min(wasted, overstock)
                donated = int(wasted * RNG.uniform(0.1, 0.4)) if wasted > 2 else 0
                wasted = wasted - donated

                effective_price = price * (1 - promo_discount) if is_promo else price
                revenue = round(sold * effective_price, 2)

                data.sales.append({
                    "store_id": store_id,
                    "product_id": pid,
                    "date": d,
                    "quantity_sold": sold,
                    "revenue": revenue,
                    "units_wasted": wasted,
                    "units_donated": donated,
                    "temperature_avg": temp,
                    "is_holiday": is_holiday,
                    "is_promotion": is_promo,
                    "promotion_discount": promo_discount,
                    "day_of_week": day_of_week,
                })

                stock = stock - sold - wasted - donated

                delivered = 0
                if day_idx % reorder_freq == 0 and day_idx > 0:
                    order_qty = max(0, reorder_point - stock + safety_stock)
                    order_qty = int(order_qty * RNG.uniform(0.9, 1.1))
                    stock += order_qty
                    delivered = order_qty
                    last_delivery = d

                days_until_expiry = max(1, shelf_days - (day_idx % max(shelf_days, 1)))

                data.inventory.append({
                    "store_id": store_id,
                    "product_id": pid,
                    "date": d,
                    "quantity_on_hand": max(0, stock),
                    "days_until_expiry": days_until_expiry,
                    "reorder_point": reorder_point,
                    "last_delivery_date": last_delivery,
                })

    return data


if __name__ == "__main__":
    result = generate_all()
    print(f"Stores:    {len(result.stores)}")
    print(f"Categories: {len(result.categories)}")
    print(f"Products:  {len(result.products)}")
    print(f"Sales:     {len(result.sales)}")
    print(f"Inventory: {len(result.inventory)}")
