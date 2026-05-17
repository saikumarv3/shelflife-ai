from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


# ── 1. stores ────────────────────────────────────────────────


class Store(Base):
    __tablename__ = "stores"

    store_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    location = Column(String(100), nullable=False)
    size_sqft = Column(Integer, nullable=False)
    type = Column(String(20), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    sales = relationship("DailySale", back_populates="store")
    inventory_snapshots = relationship("InventorySnapshot", back_populates="store")


# ── 2. categories ────────────────────────────────────────────


class Category(Base):
    __tablename__ = "categories"

    category_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False, unique=True)
    perishability = Column(String(10), nullable=False)
    avg_shelf_days = Column(Integer, nullable=False)

    products = relationship("Product", back_populates="category")


# ── 3. products ──────────────────────────────────────────────


class Product(Base):
    __tablename__ = "products"

    product_id = Column(Integer, primary_key=True, autoincrement=True)
    category_id = Column(Integer, ForeignKey("categories.category_id"), nullable=False)
    name = Column(String(100), nullable=False)
    unit_price = Column(Numeric(8, 2), nullable=False)
    cost_price = Column(Numeric(8, 2), nullable=False)
    shelf_life_days = Column(Integer, nullable=False)
    storage_temp = Column(String(10), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    category = relationship("Category", back_populates="products")
    sales = relationship("DailySale", back_populates="product")
    inventory_snapshots = relationship("InventorySnapshot", back_populates="product")


# ── 4. daily_sales ───────────────────────────────────────────


class DailySale(Base):
    __tablename__ = "daily_sales"
    __table_args__ = (UniqueConstraint("store_id", "product_id", "date", name="uq_sale_store_product_date"),)

    sale_id = Column(Integer, primary_key=True, autoincrement=True)
    store_id = Column(Integer, ForeignKey("stores.store_id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.product_id"), nullable=False, index=True)
    date = Column(Date, nullable=False)
    quantity_sold = Column(Integer, nullable=False)
    revenue = Column(Numeric(10, 2), nullable=False)
    units_wasted = Column(Integer, default=0)
    units_donated = Column(Integer, default=0)
    temperature_avg = Column(Numeric(4, 1))
    is_holiday = Column(Boolean, default=False)
    is_promotion = Column(Boolean, default=False)
    promotion_discount = Column(Numeric(4, 2), default=0.0)
    day_of_week = Column(Integer, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    store = relationship("Store", back_populates="sales")
    product = relationship("Product", back_populates="sales")


# ── 5. inventory_snapshots ───────────────────────────────────


class InventorySnapshot(Base):
    __tablename__ = "inventory_snapshots"
    __table_args__ = (UniqueConstraint("store_id", "product_id", "date", name="uq_inventory_store_product_date"),)

    snapshot_id = Column(Integer, primary_key=True, autoincrement=True)
    store_id = Column(Integer, ForeignKey("stores.store_id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.product_id"), nullable=False, index=True)
    date = Column(Date, nullable=False)
    quantity_on_hand = Column(Integer, nullable=False)
    days_until_expiry = Column(Integer)
    reorder_point = Column(Integer, nullable=False)
    last_delivery_date = Column(Date)
    created_at = Column(DateTime, server_default=func.now())

    store = relationship("Store", back_populates="inventory_snapshots")
    product = relationship("Product", back_populates="inventory_snapshots")


# ── 6. predictions ───────────────────────────────────────────


class Prediction(Base):
    __tablename__ = "predictions"
    __table_args__ = (
        UniqueConstraint(
            "store_id",
            "product_id",
            "date",
            "model_version",
            name="uq_pred_store_product_date_version",
        ),
    )

    prediction_id = Column(Integer, primary_key=True, autoincrement=True)
    store_id = Column(Integer, ForeignKey("stores.store_id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.product_id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    predicted_demand = Column(Numeric(10, 2), nullable=False)
    confidence_lower = Column(Numeric(10, 2))
    confidence_upper = Column(Numeric(10, 2))
    waste_risk_score = Column(Numeric(4, 3))
    waste_risk_tier = Column(String(10))
    actual_demand = Column(Integer)
    forecast_error = Column(Numeric(10, 4))
    model_version = Column(String(50), nullable=False)
    created_at = Column(DateTime, server_default=func.now())


# ── 7. feature_store ─────────────────────────────────────────


class FeatureRow(Base):
    __tablename__ = "feature_store"
    __table_args__ = (UniqueConstraint("store_id", "product_id", "date", name="uq_feature_store_product_date"),)

    feature_id = Column(Integer, primary_key=True, autoincrement=True)
    store_id = Column(Integer, ForeignKey("stores.store_id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.product_id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)

    # Temporal
    day_of_week = Column(Integer)
    day_of_month = Column(Integer)
    week_of_year = Column(Integer)
    month = Column(Integer)
    is_weekend = Column(Boolean)
    is_month_start = Column(Boolean)
    is_month_end = Column(Boolean)

    # Lags
    sales_lag_1d = Column(Numeric(10, 2))
    sales_lag_7d = Column(Numeric(10, 2))
    sales_lag_14d = Column(Numeric(10, 2))
    sales_lag_28d = Column(Numeric(10, 2))
    waste_lag_1d = Column(Numeric(10, 2))
    waste_lag_7d = Column(Numeric(10, 2))
    inventory_lag_1d = Column(Numeric(10, 2))

    # Rolling windows
    sales_rolling_7d_mean = Column(Numeric(10, 2))
    sales_rolling_7d_std = Column(Numeric(10, 2))
    sales_rolling_14d_mean = Column(Numeric(10, 2))
    sales_rolling_28d_mean = Column(Numeric(10, 2))
    waste_rolling_7d_sum = Column(Numeric(10, 2))
    waste_rolling_7d_rate = Column(Numeric(10, 4))
    revenue_rolling_7d = Column(Numeric(12, 2))
    sales_rolling_7d_median = Column(Numeric(10, 2))

    # Product
    unit_price = Column(Numeric(8, 2))
    cost_price = Column(Numeric(8, 2))
    shelf_life_days = Column(Integer)
    margin_pct = Column(Numeric(6, 4))
    category_encoded = Column(Integer)

    # Contextual
    is_holiday = Column(Boolean)
    is_promotion = Column(Boolean)
    promotion_discount = Column(Numeric(4, 2))
    temperature_avg = Column(Numeric(4, 1))
    store_type_encoded = Column(Integer)

    # Derived
    days_since_last_promo = Column(Integer)
    stock_to_sales_ratio = Column(Numeric(10, 4))
    days_until_expiry_norm = Column(Numeric(6, 4))

    created_at = Column(DateTime, server_default=func.now())


# ── 8. recommendations_log ───────────────────────────────────


class RecommendationLog(Base):
    __tablename__ = "recommendations_log"
    __table_args__ = (
        Index("ix_rec_store_date", "store_id", "date"),
        Index("ix_rec_product", "product_id"),
        CheckConstraint("markdown_pct >= 0 AND markdown_pct <= 100", name="ck_markdown_pct_range"),
    )

    rec_id = Column(Integer, primary_key=True, autoincrement=True)
    store_id = Column(Integer, ForeignKey("stores.store_id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.product_id"), nullable=False)
    date = Column(Date, nullable=False)
    action_type = Column(String(20), nullable=False)
    markdown_pct = Column(Integer, default=0)
    expected_waste_reduction = Column(Integer, default=0)
    expected_cost_saved_usd = Column(Numeric(10, 2), default=0)
    status = Column(String(15), nullable=False, default="pending")
    actual_waste_reduction = Column(Integer)
    actual_cost_saved_usd = Column(Numeric(10, 2))
    created_at = Column(DateTime, server_default=func.now())
    responded_at = Column(DateTime)


# ── 9. alerts ────────────────────────────────────────────────


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (Index("ix_alert_type_created", "alert_type", "created_at"),)

    alert_id = Column(Integer, primary_key=True, autoincrement=True)
    alert_type = Column(String(30), nullable=False)
    severity = Column(String(10), nullable=False)
    message = Column(Text, nullable=False)
    metadata_json = Column(JSONB)
    acknowledged = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())


# ── 10. site_visits (simple visitor tracking) ────────────────────────────────


class SiteVisit(Base):
    __tablename__ = "site_visits"

    visit_id = Column(Integer, primary_key=True, autoincrement=True)
    received_at = Column(DateTime, server_default=func.now(), nullable=False)
    source = Column(String(20))  # 'gps' | 'ip' | 'unknown'
    ip = Column(String(45))
    city = Column(String(100))
    region = Column(String(100))
    country = Column(String(100))
    latitude = Column(Numeric(9, 6))
    longitude = Column(Numeric(9, 6))
    user_agent = Column(String(512))
    path = Column(String(256))
    referrer = Column(String(256))
    payload_json = Column(JSONB)

