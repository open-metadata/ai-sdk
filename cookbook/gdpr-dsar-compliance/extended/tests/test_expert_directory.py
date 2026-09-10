from __future__ import annotations

import httpx

from expert_directory import CollateExpertDirectory, _api_root


def _catalog_transport(*, fail_data_products: bool = False) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/users":
            return httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "name": "alice.johnson",
                            "displayName": "Alice Johnson",
                            "email": "alice@jaffleshop.com",
                            "personas": [{"name": "DataSteward"}],
                            "roles": [],
                            "teams": [{"displayName": "Data Platform"}],
                            "domains": [],
                        },
                        {
                            "name": "eve.davis",
                            "displayName": "Eve Davis",
                            "email": "eve@jaffleshop.com",
                            "personas": [],
                            "roles": [],
                            "teams": [],
                            "domains": [{"displayName": "Sales"}],
                        },
                        {
                            "name": "bob.smith",
                            "displayName": "Bob Smith",
                            "email": "bob@jaffleshop.com",
                            "personas": [],
                            "roles": [],
                            "teams": [],
                            "domains": [{"displayName": "Finance"}],
                        },
                    ],
                    "paging": {},
                },
            )
        if request.url.path == "/api/v1/domains":
            return httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "name": "Sales",
                            "displayName": "Sales",
                            "description": "Customer, order, and support data",
                            "experts": [{"name": "eve.davis"}],
                        },
                        {
                            "name": "Finance",
                            "displayName": "Finance",
                            "experts": [{"name": "bob.smith"}],
                        },
                    ],
                    "paging": {},
                },
            )
        if request.url.path == "/api/v1/dataProducts":
            if fail_data_products:
                return httpx.Response(403, json={"message": "forbidden"})
            return httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "name": "Customer360",
                            "displayName": "Customer 360",
                            "description": "Curated Sales customer data",
                            "domain": {"name": "Sales"},
                            "experts": [{"name": "alice.johnson"}],
                        }
                    ],
                    "paging": {},
                },
            )
        raise AssertionError(f"Unexpected request: {request.url}")

    return httpx.MockTransport(handler)


def _directory(*, fail_data_products: bool = False) -> CollateExpertDirectory:
    client = httpx.Client(
        base_url="https://collate.example.com/api/v1",
        transport=_catalog_transport(fail_data_products=fail_data_products),
    )
    return CollateExpertDirectory(
        "https://ignored.example.com",
        "token",
        client=client,
    )


def test_api_root_accepts_host_or_api_url() -> None:
    assert (
        _api_root("https://collate.example.com") == "https://collate.example.com/api/v1"
    )
    assert (
        _api_root("https://collate.example.com/api")
        == "https://collate.example.com/api/v1"
    )
    assert _api_root("https://collate.example.com/api/v1/") == (
        "https://collate.example.com/api/v1"
    )


def test_find_candidates_combines_steward_domain_and_product_signals() -> None:
    result = _directory().find_candidates(domain_hints=["Sales"])

    assert result["warnings"] == []
    assert result["catalogCounts"] == {"users": 3, "domains": 2, "dataProducts": 1}
    candidates = {item["name"]: item for item in result["candidates"]}
    assert set(candidates) == {"alice.johnson", "eve.davis", "bob.smith"}
    assert candidates["alice.johnson"]["personas"] == ["DataSteward"]
    assert {signal["type"] for signal in candidates["alice.johnson"]["signals"]} == {
        "data_steward",
        "data_product_expert",
    }
    assert candidates["eve.davis"]["signals"] == [
        {"type": "domain_expert", "scope": "Sales", "matchesRequest": True}
    ]
    assert candidates["eve.davis"]["eligibleForRecommendation"] is True
    assert candidates["bob.smith"]["signals"] == [
        {"type": "domain_expert", "scope": "Finance", "matchesRequest": False}
    ]
    assert candidates["bob.smith"]["eligibleForRecommendation"] is False


def test_optional_endpoint_failure_returns_partial_context_with_warning() -> None:
    result = _directory(fail_data_products=True).find_candidates(domain_hints=["Sales"])

    assert {item["name"] for item in result["candidates"]} == {
        "alice.johnson",
        "eve.davis",
        "bob.smith",
    }
    assert len(result["warnings"]) == 1
    assert result["warnings"][0].startswith("Could not read data products:")
