"""Deterministic risk scoring for impact-analysis reports."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Sequence

from diff_parser import ChangedAsset


class RiskLevel(str, Enum):
    """Human-facing risk labels for PR comments and workflow outputs."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class ImpactScore:
    """Risk score summary derived from analysis text and changed assets."""

    level: RiskLevel
    affected_count: int
    reasons: list[str]


PII_PATTERN = re.compile(
    r"\b(pii|sensitive|email|ssn|card|ip_address|phone|address|gdpr|ccpa)\b",
    re.IGNORECASE,
)
QUALITY_PATTERN = re.compile(
    r"\b(data quality|dq|test|tests|not_null|unique|accepted_values|fail|failing)\b",
    re.IGNORECASE,
)
CRITICAL_BUSINESS_PATTERN = re.compile(
    r"\b(finance|revenue|executive|board|dashboard|sla|critical|sox)\b",
    re.IGNORECASE,
)
NO_DOWNSTREAM_PATTERN = re.compile(
    r"\b(no downstream assets|no assets are .*affected|no affected assets)\b",
    re.IGNORECASE,
)
MARKDOWN_LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def score_impact(analysis_text: str, changed_assets: Sequence[ChangedAsset]) -> ImpactScore:
    """Score risk from report content without trusting the LLM for the label."""

    affected_count = _affected_count(analysis_text)
    points = 0
    reasons: list[str] = []

    if affected_count >= 5:
        points += 3
        reasons.append("many downstream assets detected")
    elif affected_count >= 3:
        points += 2
        reasons.append("multiple downstream assets detected")
    elif affected_count > 0:
        points += 1
        reasons.append("downstream assets detected")

    if any(asset.change_type == "deleted" for asset in changed_assets):
        points += 2
        reasons.append("model or schema deletion detected")

    if PII_PATTERN.search(analysis_text):
        points += 2
        reasons.append("PII or sensitive data mentioned")

    if QUALITY_PATTERN.search(analysis_text):
        points += 1
        reasons.append("data quality impact mentioned")

    if CRITICAL_BUSINESS_PATTERN.search(analysis_text):
        points += 2
        reasons.append("critical business asset mentioned")

    if affected_count == 0 and NO_DOWNSTREAM_PATTERN.search(analysis_text):
        points = min(points, 1)
        reasons = ["no downstream assets detected"]

    return ImpactScore(
        level=_risk_level(points),
        affected_count=affected_count,
        reasons=reasons or ["no material risk signals detected"],
    )


def _affected_count(analysis_text: str) -> int:
    links = {
        match.group(1)
        for match in MARKDOWN_LINK_PATTERN.finditer(analysis_text)
        if "/table/" in match.group(1)
        or "/dashboard/" in match.group(1)
        or "/pipeline/" in match.group(1)
        or "/chart/" in match.group(1)
    }
    return len(links)


def _risk_level(points: int) -> RiskLevel:
    if points >= 6:
        return RiskLevel.CRITICAL
    if points >= 4:
        return RiskLevel.HIGH
    if points >= 2:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW
