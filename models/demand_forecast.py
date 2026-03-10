"""
Demand forecast model — XGBoost + LightGBM weighted ensemble with
quantile regression for confidence intervals.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from xgboost import XGBRegressor
from lightgbm import LGBMRegressor


@dataclass
class DemandForecaster:
    """Trains and predicts with an XGBoost + LightGBM ensemble."""

    xgb_params: dict = field(default_factory=lambda: {
        "n_estimators": 300,
        "max_depth": 6,
        "learning_rate": 0.05,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "min_child_weight": 3,
        "reg_alpha": 0.01,
        "reg_lambda": 1.5,
        "random_state": 42,
        "n_jobs": -1,
    })
    lgbm_params: dict = field(default_factory=lambda: {
        "n_estimators": 300,
        "max_depth": -1,
        "learning_rate": 0.05,
        "num_leaves": 63,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "min_child_samples": 10,
        "reg_alpha": 0.01,
        "reg_lambda": 1.5,
        "random_state": 42,
        "n_jobs": -1,
        "verbose": -1,
    })
    ensemble_weight_xgb: float = 0.6

    xgb_model: XGBRegressor | None = field(default=None, repr=False)
    lgbm_model: LGBMRegressor | None = field(default=None, repr=False)
    xgb_lower: XGBRegressor | None = field(default=None, repr=False)
    xgb_upper: XGBRegressor | None = field(default=None, repr=False)

    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray | None = None,
        y_val: np.ndarray | None = None,
    ) -> dict[str, float]:
        """Train all models. Returns training summary metrics."""
        eval_set = [(X_val, y_val)] if X_val is not None else None

        self.xgb_model = XGBRegressor(**self.xgb_params)
        self.xgb_model.fit(
            X_train, y_train,
            eval_set=eval_set,
            verbose=False,
        )

        self.lgbm_model = LGBMRegressor(**self.lgbm_params)
        lgbm_callbacks = []
        self.lgbm_model.fit(
            X_train, y_train,
            eval_set=eval_set,
            callbacks=lgbm_callbacks,
        )

        # Quantile models for confidence intervals
        lower_params = {**self.xgb_params, "objective": "reg:quantileerror", "quantile_alpha": 0.05}
        upper_params = {**self.xgb_params, "objective": "reg:quantileerror", "quantile_alpha": 0.95}

        self.xgb_lower = XGBRegressor(**lower_params)
        self.xgb_lower.fit(X_train, y_train, verbose=False)

        self.xgb_upper = XGBRegressor(**upper_params)
        self.xgb_upper.fit(X_train, y_train, verbose=False)

        return {"status": "trained", "n_train": len(X_train)}

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Return ensemble point prediction."""
        w = self.ensemble_weight_xgb
        xgb_pred = self.xgb_model.predict(X)
        lgbm_pred = self.lgbm_model.predict(X)
        return np.maximum(0, w * xgb_pred + (1 - w) * lgbm_pred)

    def predict_with_intervals(self, X: np.ndarray) -> dict[str, np.ndarray]:
        """Return point prediction + 90% confidence interval."""
        point = self.predict(X)
        lower = np.maximum(0, self.xgb_lower.predict(X))
        upper = np.maximum(0, self.xgb_upper.predict(X))
        return {"predicted_demand": point, "confidence_lower": lower, "confidence_upper": upper}

    def get_feature_importance(self, feature_names: list[str]) -> dict[str, float]:
        """Return XGBoost feature importances as a dict."""
        importances = self.xgb_model.feature_importances_
        return dict(sorted(zip(feature_names, importances), key=lambda x: -x[1]))
