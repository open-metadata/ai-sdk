from __future__ import annotations

from diff_parser import ChangedAsset
from risk_scoring import RiskLevel, score_impact


def test_score_impact_marks_no_downstream_additive_change_low_risk() -> None:
    score = score_impact(
        "No downstream assets are affected. This additive change has no PII or data quality impact.",
        [ChangedAsset("dim_customers", "models/marts/dim_customers.sql", "model", "modified", "")],
    )

    assert score.level is RiskLevel.LOW
    assert score.affected_count == 0


def test_score_impact_marks_finance_pii_and_quality_breakage_critical() -> None:
    analysis = """
## Affected Assets
- [fct_daily_revenue](https://metadata/table/fct_daily_revenue) Owner: Finance
- [Executive Revenue Dashboard](https://metadata/dashboard/revenue) Owner: CFO
- [fct_orders](https://metadata/table/fct_orders) Owner: Analytics

## Risk Assessment
- Data Quality: uniqueness tests may fail
- Compliance: billing_email, card_last_four, and ip_address are PII
- Business: finance dashboard and board report are affected
"""

    score = score_impact(
        analysis,
        [ChangedAsset("stg_stripe__payments", "models/staging/stg_stripe__payments.sql", "model", "modified", "")],
    )

    assert score.level is RiskLevel.CRITICAL
    assert score.affected_count == 3
    assert "PII or sensitive data mentioned" in score.reasons
    assert "critical business asset mentioned" in score.reasons
