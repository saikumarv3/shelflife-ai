"""Action type definitions for the recommendation engine."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ActionType:
    name: str
    description_template: str
    min_risk: float
    max_risk: float
    confidence_base: float
    markdown_pct: int


ACTION_TYPES: list[ActionType] = [
    ActionType(
        name="adjust_order",
        description_template="Reduce next order by {reduction} units (from {current} to {target})",
        min_risk=0.2, max_risk=1.0, confidence_base=0.90,
        markdown_pct=0,
    ),
    ActionType(
        name="markdown",
        description_template="Apply {pct}% markdown to {product_name}",
        min_risk=0.4, max_risk=1.0, confidence_base=0.80,
        markdown_pct=25,
    ),
    ActionType(
        name="bundle",
        description_template="Create bundle: {product_name} + complementary item at 15% off",
        min_risk=0.3, max_risk=0.8, confidence_base=0.65,
        markdown_pct=15,
    ),
    ActionType(
        name="redistribute",
        description_template="Transfer {units} units to higher-demand store",
        min_risk=0.5, max_risk=1.0, confidence_base=0.70,
        markdown_pct=0,
    ),
    ActionType(
        name="donate",
        description_template="Donate {units} units of {product_name} to local food bank",
        min_risk=0.7, max_risk=1.0, confidence_base=0.95,
        markdown_pct=0,
    ),
]
