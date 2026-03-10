"""Recommendation engine — rule-based triggers + ML scoring pipeline."""

from __future__ import annotations

from recommendation.actions import ACTION_TYPES


class RecommendationEngine:
    """Generates ranked recommendations for a product-store based on risk and inventory."""

    def generate(
        self,
        store_id: int,
        product_id: int,
        product_name: str,
        waste_risk_score: float,
        predicted_demand: float,
        current_stock: int,
        unit_price: float,
        cost_price: float,
        days_until_expiry: int | None = None,
    ) -> list[dict]:
        excess = max(0, int(current_stock - predicted_demand))
        margin = unit_price - cost_price
        recommendations = []

        for action in ACTION_TYPES:
            if not (action.min_risk <= waste_risk_score <= action.max_risk):
                continue

            rec = self._build_recommendation(
                action=action,
                product_name=product_name,
                excess=excess,
                current_stock=current_stock,
                predicted_demand=predicted_demand,
                waste_risk_score=waste_risk_score,
                unit_price=unit_price,
                cost_price=cost_price,
                margin=margin,
                days_until_expiry=days_until_expiry,
            )
            if rec:
                recommendations.append(rec)

        recommendations.sort(key=lambda r: -r["expected_impact"]["waste_cost_saved_usd"])

        for i, rec in enumerate(recommendations, 1):
            rec["priority"] = i

        return recommendations

    def _build_recommendation(
        self, *, action, product_name, excess, current_stock, predicted_demand,
        waste_risk_score, unit_price, cost_price, margin, days_until_expiry,
    ) -> dict | None:
        waste_units = max(1, int(excess * waste_risk_score))

        if action.name == "markdown":
            pct = self._compute_markdown_pct(waste_risk_score, days_until_expiry)
            desc = action.description_template.format(pct=pct, product_name=product_name)
            sell_through = min(waste_units, int(waste_units * (pct / 100 + 0.5)))
            revenue_loss = -round(sell_through * unit_price * pct / 100, 2)
            saved = round(sell_through * cost_price, 2)

        elif action.name == "bundle":
            desc = action.description_template.format(product_name=product_name)
            sell_through = max(1, waste_units // 2)
            revenue_loss = round(sell_through * unit_price * 0.15, 2)
            saved = round(sell_through * cost_price, 2)

        elif action.name == "donate":
            donate_units = max(1, waste_units)
            desc = action.description_template.format(units=donate_units, product_name=product_name)
            sell_through = donate_units
            revenue_loss = 0.0
            saved = round(donate_units * cost_price, 2)

        elif action.name == "adjust_order":
            reduction = max(1, excess)
            target = max(0, current_stock - reduction)
            desc = action.description_template.format(
                reduction=reduction, current=current_stock, target=target
            )
            sell_through = reduction
            revenue_loss = 0.0
            saved = round(reduction * cost_price, 2)

        elif action.name == "redistribute":
            transfer_units = max(1, excess // 2)
            desc = action.description_template.format(units=transfer_units)
            sell_through = transfer_units
            revenue_loss = 0.0
            saved = round(transfer_units * cost_price, 2)
        else:
            return None

        confidence = min(1.0, action.confidence_base * (0.5 + waste_risk_score * 0.5))

        return {
            "action": action.name,
            "priority": 0,
            "description": desc,
            "expected_impact": {
                "waste_reduction_units": sell_through,
                "revenue_impact_usd": revenue_loss,
                "waste_cost_saved_usd": saved,
            },
            "confidence": round(confidence, 2),
        }

    @staticmethod
    def _compute_markdown_pct(risk: float, days_until_expiry: int | None) -> int:
        if days_until_expiry is not None and days_until_expiry <= 1:
            return 50
        if risk >= 0.8:
            return 40
        if risk >= 0.6:
            return 25
        return 15
