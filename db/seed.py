"""
Populate the database with synthetic data.

Usage:
    uv run python -m db.seed
"""

from __future__ import annotations

import time

from data_generator.synthetic import generate_all
from db.models import (
    Base,
    Category,
    DailySale,
    InventorySnapshot,
    Product,
    Store,
)
from db.session import SessionLocal, engine


def seed() -> None:
    print("=" * 60)
    print("ShelfLife AI — Database Seeder")
    print("=" * 60)

    # ── Create tables ─────────────────────────────────────
    print("\n[1/5] Creating tables...")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    print("       9 tables created.")

    # ── Generate data ─────────────────────────────────────
    print("\n[2/5] Generating synthetic data...")
    t0 = time.perf_counter()
    data = generate_all()
    gen_time = time.perf_counter() - t0
    print(f"       Generated in {gen_time:.1f}s:")
    print(f"         Stores:     {len(data.stores)}")
    print(f"         Categories: {len(data.categories)}")
    print(f"         Products:   {len(data.products)}")
    print(f"         Sales:      {len(data.sales):,}")
    print(f"         Inventory:  {len(data.inventory):,}")

    # ── Insert reference data ─────────────────────────────
    print("\n[3/5] Inserting stores, categories, products...")
    db = SessionLocal()
    try:
        for s in data.stores:
            db.add(Store(**s))
        for c in data.categories:
            db.add(Category(**c))
        for p in data.products:
            db.add(Product(**p))
        db.commit()
        print(f"       {len(data.stores)} stores, {len(data.categories)} categories, {len(data.products)} products inserted.")

        # ── Bulk insert sales ─────────────────────────────
        print(f"\n[4/5] Inserting {len(data.sales):,} daily_sales rows (bulk)...")
        t0 = time.perf_counter()
        BATCH = 5000
        for i in range(0, len(data.sales), BATCH):
            batch = data.sales[i : i + BATCH]
            db.bulk_insert_mappings(DailySale, batch)
            if (i // BATCH) % 2 == 0:
                pct = min(100, int(i / len(data.sales) * 100))
                print(f"       ... {pct}%")
        db.commit()
        sales_time = time.perf_counter() - t0
        print(f"       Sales inserted in {sales_time:.1f}s")

        # ── Bulk insert inventory ─────────────────────────
        print(f"\n[5/5] Inserting {len(data.inventory):,} inventory_snapshots rows (bulk)...")
        t0 = time.perf_counter()
        for i in range(0, len(data.inventory), BATCH):
            batch = data.inventory[i : i + BATCH]
            db.bulk_insert_mappings(InventorySnapshot, batch)
        db.commit()
        inv_time = time.perf_counter() - t0
        print(f"       Inventory inserted in {inv_time:.1f}s")

    finally:
        db.close()

    # ── Verify ────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("VERIFICATION")
    print("=" * 60)
    db = SessionLocal()
    try:
        counts = {
            "stores": db.query(Store).count(),
            "categories": db.query(Category).count(),
            "products": db.query(Product).count(),
            "daily_sales": db.query(DailySale).count(),
            "inventory_snapshots": db.query(InventorySnapshot).count(),
        }
        for table, count in counts.items():
            status = "OK" if count > 0 else "EMPTY"
            print(f"  {table:25s} {count:>8,}  [{status}]")

        total_revenue = db.query(DailySale.revenue).with_entities(DailySale.revenue).all()
        revenue_sum = sum(float(r[0]) for r in total_revenue)

        total_waste = db.query(DailySale.units_wasted).all()
        waste_sum = sum(r[0] for r in total_waste)

        total_donated = db.query(DailySale.units_donated).all()
        donated_sum = sum(r[0] for r in total_donated)

        print(f"\n  Total revenue:      ${revenue_sum:>12,.2f}")
        print(f"  Total units wasted: {waste_sum:>12,}")
        print(f"  Total units donated:{donated_sum:>12,}")

    finally:
        db.close()

    print("\n" + "=" * 60)
    print("Seed complete!")
    print("=" * 60)


if __name__ == "__main__":
    seed()
