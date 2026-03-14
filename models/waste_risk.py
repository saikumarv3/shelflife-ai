"""
Waste risk classifier — XGBoost binary classifier that predicts whether
a product-store-day will experience waste within the next 3 days.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from xgboost import XGBClassifier

from config.settings import settings


@dataclass
class WasteRiskClassifier:
    """Binary waste risk classifier using XGBoost."""

    params: dict = field(
        default_factory=lambda: {
            "n_estimators": 300,
            "max_depth": 6,
            "learning_rate": 0.05,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "min_child_weight": 3,
            "reg_alpha": 0.01,
            "reg_lambda": 1.5,
            "random_state": settings.random_seed,
            "n_jobs": -1,
            "eval_metric": "logloss",
        }
    )
    model: XGBClassifier | None = field(default=None, repr=False)

    RISK_TIERS = [
        (0.0, 0.2, "low"),
        (0.2, 0.5, "medium"),
        (0.5, 0.8, "high"),
        (0.8, 1.01, "critical"),
    ]

    @staticmethod
    def build_labels(sales_df: pd.DataFrame) -> pd.Series:
        """
        Construct binary labels: 1 if units_wasted > 0 within the next 3 days
        for this store-product group.
        """
        df = sales_df.sort_values(["store_id", "product_id", "date"]).copy()
        df["_future_waste"] = df.groupby(["store_id", "product_id"])["units_wasted"].transform(
            lambda x: x.shift(-1).rolling(3, min_periods=1).sum()
        )
        return (df["_future_waste"] > 0).astype(int)

    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray | None = None,
        y_val: np.ndarray | None = None,
    ) -> dict:
        """Train the classifier with automatic class imbalance handling."""
        pos = y_train.sum()
        neg = len(y_train) - pos
        scale = neg / max(pos, 1)

        self.model = XGBClassifier(**self.params, scale_pos_weight=scale)
        eval_set = [(X_val, y_val)] if X_val is not None else None
        self.model.fit(X_train, y_train, eval_set=eval_set, verbose=False)

        return {
            "status": "trained",
            "n_train": len(X_train),
            "pos_rate": float(pos / len(y_train)),
            "scale_pos_weight": round(scale, 2),
        }

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Return probability of waste (positive class)."""
        return self.model.predict_proba(X)[:, 1]

    def predict_tier(self, X: np.ndarray) -> list[str]:
        """Return risk tier string for each sample."""
        probs = self.predict_proba(X)
        return [self._prob_to_tier(p) for p in probs]

    def _prob_to_tier(self, prob: float) -> str:
        for low, high, tier in self.RISK_TIERS:
            if low <= prob < high:
                return tier
        return "critical"
