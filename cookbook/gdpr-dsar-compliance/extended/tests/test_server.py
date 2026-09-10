from __future__ import annotations

import json
from types import SimpleNamespace

from server import (
    ExtendedGDPRRuntime,
    GDPRHandoffWorkflow,
    ExpertDirectoryTool,
    ExpertDirectoryInput,
    GDPRAnalysisTool,
    GDPRAnalysisInput,
    OptionalLangfuseTracing,
    _invoke_ai_studio_agent,
    _needs_continuation,
)


class _FakeAgent:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None]] = []

    def call(self, message: str, *, conversation_id: str | None = None):
        self.calls.append((message, conversation_id))
        if len(self.calls) == 1:
            return SimpleNamespace(
                response="I found the customer tables. Next I will inspect details:",
                conversation_id="conv-1",
                tools_used=["search_metadata"],
            )
        return SimpleNamespace(
            response="## Compliance report\n\n| Asset | Risk |\n| --- | --- |\n| customers | PII |",
            conversation_id="conv-1",
            tools_used=["get_asset_context"],
        )


class _FakeDirectory:
    def find_candidates(self, *, domain_hints, max_candidates):
        return {
            "domainHints": domain_hints,
            "maxCandidates": max_candidates,
            "candidates": [
                {
                    "name": "alice.johnson",
                    "email": "alice@example.com",
                    "eligibleForRecommendation": True,
                    "signals": [{"type": "data_steward", "scope": "organization"}],
                }
            ],
            "catalogCounts": {"users": 1, "domains": 2, "dataProducts": 1},
            "warnings": [],
        }


class _FakeModel:
    def __init__(self) -> None:
        self.calls = []

    def invoke(self, messages, config=None):
        self.calls.append((messages, config))
        return SimpleNamespace(
            content=(
                "## Recommended assignees\n\n"
                "| Name | Contact | Catalog evidence | Proposed responsibility |\n"
                "| --- | --- | --- | --- |\n"
                "| Alice | alice@example.com | Data Steward | Coordinate |\n\n"
                "## Handoff\n\n1. Obtain human approval."
            )
        )


def test_ai_studio_delegate_continues_same_conversation() -> None:
    agent = _FakeAgent()

    result = _invoke_ai_studio_agent(agent, "Delete Michael Perez")

    assert result["turns"] == 2
    assert result["collateToolsUsed"] == ["search_metadata", "get_asset_context"]
    assert agent.calls[0] == ("Delete Michael Perez", None)
    assert agent.calls[1][1] == "conv-1"


def test_completion_heuristic_distinguishes_report_from_narration() -> None:
    assert _needs_continuation("Now I'll trace the lineage:") is True
    assert _needs_continuation("## Report\n\nComplete.") is False


def test_custom_tool_inputs_publish_json_schemas() -> None:
    gdpr_schema = GDPRAnalysisInput.model_json_schema()
    expert_schema = ExpertDirectoryInput.model_json_schema()

    assert gdpr_schema["required"] == ["request"]
    assert gdpr_schema["properties"]["request"]["type"] == "string"
    assert expert_schema["properties"]["domain_hints"]["type"] == "array"
    assert expert_schema["properties"]["max_candidates"]["maximum"] == 50


def test_langchain_tools_execute_wrapped_dependencies() -> None:
    gdpr_result = json.loads(
        GDPRAnalysisTool(_FakeAgent()).invoke({"request": "Delete Michael Perez"})
    )
    expert_result = json.loads(
        ExpertDirectoryTool(_FakeDirectory()).invoke(
            {"domain_hints": ["Sales"], "max_candidates": 4}
        )
    )

    assert gdpr_result["turns"] == 2
    assert expert_result["domainHints"] == ["Sales"]
    assert expert_result["maxCandidates"] == 4


def test_langgraph_exposes_and_runs_the_collate_internal_boundary() -> None:
    model = _FakeModel()
    workflow = GDPRHandoffWorkflow(
        GDPRAnalysisTool(_FakeAgent()),
        ExpertDirectoryTool(_FakeDirectory()),
        model,
    )

    events = list(
        workflow.graph.stream(
            {"request": "Delete Michael Perez", "tools_used": [], "execution": []},
            stream_mode="updates",
        )
    )

    assert [next(iter(event)) for event in events] == [
        "collate_gdpr_agent",
        "collate_expert_directory",
        "internal_handoff_agent",
    ]
    final_update = events[-1]["internal_handoff_agent"]
    assert "## Compliance analysis" in final_update["response"]
    assert "## Recommended assignees" in final_update["response"]
    assert len(model.calls) == 1
    model_input = model.calls[0][0][1].content
    assert "AUTHORITATIVE AI STUDIO COMPLIANCE REPORT" in model_input
    assert "alice.johnson" in model_input

    mermaid = workflow.graph.get_graph().draw_mermaid()
    assert "collate_gdpr_agent" in mermaid
    assert "collate_expert_directory" in mermaid
    assert "internal_handoff_agent" in mermaid


def test_runtime_stream_reports_each_node_and_the_nested_tool_levels(
    monkeypatch,
) -> None:
    monkeypatch.delenv("LANGFUSE_ENABLED", raising=False)
    runtime = object.__new__(ExtendedGDPRRuntime)
    runtime._workflow = GDPRHandoffWorkflow(  # noqa: SLF001
        GDPRAnalysisTool(_FakeAgent()),
        ExpertDirectoryTool(_FakeDirectory()),
        _FakeModel(),
    )
    runtime._tracing = OptionalLangfuseTracing()  # noqa: SLF001

    events = list(runtime.stream("Delete Michael Perez"))

    assert [event["type"] for event in events] == ["node", "node", "node", "result"]
    result = events[-1]
    assert result["toolsUsed"] == [
        "analyze_gdpr_request",
        "find_data_stewards_and_experts",
    ]
    assert result["collateToolsUsed"] == ["search_metadata", "get_asset_context"]
    assert [step["node"] for step in result["execution"]] == [
        "collate_gdpr_agent",
        "collate_expert_directory",
        "internal_handoff_agent",
    ]
    assert result["traceUrl"] is None
