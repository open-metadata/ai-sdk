"""Discover human handoff candidates from governed Collate metadata.

The directory deliberately has no hard-coded people. It combines three live
catalog signals:

* users assigned a Data Steward role or persona;
* experts assigned to Domains; and
* experts assigned to Data Products.

Every request uses the same JWT as the rest of the demo, so Collate remains the
authorization boundary for what the internal workflow can see.
"""

from __future__ import annotations

import re
from typing import Any

import httpx


def _api_root(host: str) -> str:
    root = host.rstrip("/")
    if root.endswith("/api/v1"):
        return root
    if root.endswith("/api"):
        return f"{root}/v1"
    return f"{root}/api/v1"


def _normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def _reference_name(reference: dict[str, Any]) -> str | None:
    value = reference.get("fullyQualifiedName") or reference.get("name")
    return str(value) if value else None


def _references(entity: dict[str, Any], field: str) -> list[dict[str, Any]]:
    value = entity.get(field) or []
    if isinstance(value, dict):
        return [value]
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _display_names(references: list[dict[str, Any]]) -> list[str]:
    names = []
    for reference in references:
        value = reference.get("displayName") or reference.get("name")
        if value:
            names.append(str(value))
    return names


def _matches_hints(entity: dict[str, Any], hints: list[str]) -> bool:
    if not hints:
        return False
    searchable = _normalized(
        " ".join(
            str(entity.get(field) or "")
            for field in ("name", "fullyQualifiedName", "displayName", "description")
        )
    )
    return any(
        normalized_hint
        and (normalized_hint in searchable or searchable in normalized_hint)
        for hint in hints
        if (normalized_hint := _normalized(hint))
    )


def _is_data_steward(user: dict[str, Any]) -> bool:
    assignments = _references(user, "roles") + _references(user, "personas")
    assignment_names = {
        _normalized(str(item.get("name") or item.get("displayName") or ""))
        for item in assignments
    }
    if "datasteward" in assignment_names:
        return True
    return "data steward" in str(user.get("description") or "").casefold()


class CollateExpertDirectory:
    """Read users and expert relationships from the Collate REST API."""

    def __init__(
        self,
        host: str,
        token: str,
        *,
        timeout: float = 30.0,
        verify_ssl: bool = True,
        client: httpx.Client | None = None,
    ) -> None:
        self._owns_client = client is None
        self._client = client or httpx.Client(
            base_url=_api_root(host),
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "User-Agent": "collate-gdpr-handoff-demo/1.0",
            },
            timeout=timeout,
            verify=verify_ssl,
        )

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def _list_all(self, path: str, *, fields: str) -> list[dict[str, Any]]:
        entities: list[dict[str, Any]] = []
        after: str | None = None
        while True:
            params: dict[str, str | int | bool] = {
                "fields": fields,
                "limit": 100,
            }
            if path == "/users":
                params["isBot"] = False
            if after:
                params["after"] = after

            response = self._client.get(path, params=params)
            response.raise_for_status()
            payload = response.json()
            data = payload.get("data", []) if isinstance(payload, dict) else []
            entities.extend(item for item in data if isinstance(item, dict))

            paging = payload.get("paging") or {}
            after = paging.get("after")
            if not after:
                return entities

    def find_candidates(
        self,
        *,
        domain_hints: list[str] | None = None,
        max_candidates: int = 12,
    ) -> dict[str, Any]:
        """Return catalog-backed stewards and experts, ranked by scope hints.

        A missing or unauthorized optional endpoint does not erase results from
        the others. The warnings field makes partial context explicit to the
        calling agent.
        """
        hints = [hint.strip() for hint in (domain_hints or []) if hint.strip()]
        warnings: list[str] = []

        def load(label: str, path: str, fields: str) -> list[dict[str, Any]]:
            try:
                return self._list_all(path, fields=fields)
            except (httpx.HTTPError, ValueError) as exc:
                warnings.append(f"Could not read {label}: {exc}")
                return []

        users = load("users", "/users", "teams,roles,personas,domains")
        domains = load("domains", "/domains", "experts")
        data_products = load(
            "data products",
            "/dataProducts",
            "domain,experts",
        )

        users_by_name = {
            name.casefold(): user
            for user in users
            if (name := _reference_name(user)) is not None
        }
        candidates: dict[str, dict[str, Any]] = {}

        def candidate_for(reference: dict[str, Any]) -> dict[str, Any] | None:
            name = _reference_name(reference)
            if not name:
                return None
            user = users_by_name.get(name.casefold(), reference)
            key = name.casefold()
            if key not in candidates:
                candidates[key] = {
                    "name": name,
                    "displayName": user.get("displayName")
                    or reference.get("displayName")
                    or name,
                    "email": user.get("email"),
                    "description": user.get("description"),
                    "teams": _display_names(_references(user, "teams")),
                    "roles": _display_names(_references(user, "roles")),
                    "personas": _display_names(_references(user, "personas")),
                    "domains": _display_names(_references(user, "domains")),
                    "signals": [],
                    "_score": 0,
                }
            return candidates[key]

        def add_signal(
            candidate: dict[str, Any],
            *,
            signal_type: str,
            scope: str,
            relevant: bool,
        ) -> None:
            signal = {"type": signal_type, "scope": scope, "matchesRequest": relevant}
            if signal not in candidate["signals"]:
                candidate["signals"].append(signal)
                candidate["_score"] += 60 if relevant else 10

        for user in users:
            if not _is_data_steward(user):
                continue
            candidate = candidate_for(user)
            if candidate is not None:
                add_signal(
                    candidate,
                    signal_type="data_steward",
                    scope="organization",
                    relevant=True,
                )
                candidate["_score"] += 40

        for domain in domains:
            scope = str(
                domain.get("displayName")
                or domain.get("fullyQualifiedName")
                or domain.get("name")
                or "Unknown domain"
            )
            relevant = _matches_hints(domain, hints)
            for expert in _references(domain, "experts"):
                candidate = candidate_for(expert)
                if candidate is not None:
                    add_signal(
                        candidate,
                        signal_type="domain_expert",
                        scope=scope,
                        relevant=relevant,
                    )

        for product in data_products:
            scope = str(
                product.get("displayName")
                or product.get("fullyQualifiedName")
                or product.get("name")
                or "Unknown data product"
            )
            relevant = _matches_hints(product, hints)
            domain_refs = _references(product, "domain")
            if domain_refs:
                relevant = relevant or any(
                    _matches_hints(domain, hints) for domain in domain_refs
                )
            for expert in _references(product, "experts"):
                candidate = candidate_for(expert)
                if candidate is not None:
                    add_signal(
                        candidate,
                        signal_type="data_product_expert",
                        scope=scope,
                        relevant=relevant,
                    )

        ranked = sorted(
            candidates.values(),
            key=lambda item: (-item["_score"], str(item["displayName"]).casefold()),
        )
        for candidate in ranked:
            candidate.pop("_score", None)
            candidate["eligibleForRecommendation"] = not hints or any(
                signal["type"] == "data_steward" or signal["matchesRequest"]
                for signal in candidate["signals"]
            )

        return {
            "domainHints": hints,
            "candidates": ranked[: max(1, min(max_candidates, 50))],
            "catalogCounts": {
                "users": len(users),
                "domains": len(domains),
                "dataProducts": len(data_products),
            },
            "warnings": warnings,
        }
