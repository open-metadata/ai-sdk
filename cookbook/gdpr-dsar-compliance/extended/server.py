"""Extended GDPR demo: an observable LangGraph around Collate context.

LangGraph makes the application-owned workflow explicit. The graph delegates
the data/compliance investigation to the existing AI Studio GDPR agent, loads
current human expertise from Collate, and leaves only case routing and
presentation to the application's model.

Run from the repository root:

    PYTHONPATH=python/src python cookbook/gdpr-dsar-compliance/extended/server.py
"""

from __future__ import annotations

import json
import operator
import os
import re
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from time import perf_counter
from typing import Annotated, Any, TypedDict

from langchain.chat_models import init_chat_model
from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool, ToolException
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field, PrivateAttr

from ai_sdk import AISdk, AISdkConfig

from expert_directory import CollateExpertDirectory


AGENT_NAME = os.getenv("AI_SDK_AGENT", "GDPRComplianceAnalyzer")
MODEL = os.getenv("DEMO_MODEL", "openai:gpt-4o")
PORT = int(os.getenv("PORT", "8081"))
MAX_TURNS = int(os.getenv("AI_SDK_MAX_TURNS", "8"))
FRONTEND = Path(__file__).resolve().parent.parent / "index.html"
CONTINUE_MESSAGE = "Continue and finish the complete compliance report."


INTERNAL_AGENT_PROMPT = """You are the application-owned handoff agent for a
GDPR case. Collate's AI Studio agent has already performed the authoritative
data and compliance analysis. Do not redo, challenge, or embellish that work.

Your responsibilities are deliberately narrow:
1. Match the affected assets and domains in the compliance report to the live
   steward/expert signals returned by the Collate directory tool.
2. Return a "## Recommended assignees" Markdown table with Name, Contact,
   Catalog evidence, and Proposed responsibility.
3. Return a "## Handoff" section with a short ordered action plan.

Only recommend candidates whose eligibleForRecommendation field is true.
Explain every recommendation with its catalog signals (Data Steward persona or
role, Domain expert, or Data Product expert). Never invent people, titles,
expertise, email addresses, or completed assignments. State explicitly that a
human still needs to approve and assign the case. If the directory is partial
or empty, preserve its warnings and say that the available context is
insufficient. Return only the two requested sections; the application preserves
the AI Studio compliance report separately and will prepend it unchanged.
"""


WORKFLOW_NODES: list[dict[str, Any]] = [
    {
        "id": "collate_gdpr_agent",
        "label": "GDPR Agent",
        "owner": "Collate AI Studio",
        "ownerKey": "collate",
        "kind": "Delegated agent",
        "does": (
            "Searches only the governed Jaffle Shop scope, retrieves asset context, "
            "traces lineage, identifies PII, and evaluates retention conflicts."
        ),
        "output": "Authoritative compliance report + the Collate tools it used",
    },
    {
        "id": "collate_expert_directory",
        "label": "Expert directory tool",
        "owner": "Our tool → Collate",
        "ownerKey": "bridge",
        "kind": "Governed context lookup",
        "does": (
            "Lists current Data Stewards plus Domain and Data Product experts under "
            "the same token's permissions."
        ),
        "output": "Structured candidates, catalog evidence, and RBAC warnings",
    },
    {
        "id": "internal_handoff_agent",
        "label": "Internal agent",
        "owner": "Our LangGraph app",
        "ownerKey": "internal",
        "kind": "Application reasoning",
        "does": (
            "Matches findings to eligible people and writes the recommendation and "
            "human-approval handoff. It does not rediscover data context."
        ),
        "output": "Recommended assignees + ordered handoff plan",
    },
]

WORKFLOW_EDGES = [
    {"from": "collate_gdpr_agent", "to": "collate_expert_directory"},
    {"from": "collate_expert_directory", "to": "internal_handoff_agent"},
]


def _needs_continuation(text: str) -> bool:
    """Recognize an AI Studio response that is narrating unfinished work."""
    stripped = text.rstrip()
    if stripped.endswith(":"):
        return True
    if re.search(r"\b(let me|now I'll|I'll now|next,? I)\b[^.!]*$", stripped, re.I):
        return True
    return bool(stripped) and "##" not in stripped and "| " not in stripped


def _invoke_ai_studio_agent(agent: Any, request: str) -> dict[str, Any]:
    """Invoke the AI Studio agent until it emits a complete-looking report."""
    result = agent.call(request)
    conversation_id = result.conversation_id
    best_response = result.response
    tools_used = list(result.tools_used)
    turns = 1

    while _needs_continuation(best_response) and turns < MAX_TURNS and conversation_id:
        turns += 1
        result = agent.call(CONTINUE_MESSAGE, conversation_id=conversation_id)
        conversation_id = result.conversation_id
        tools_used.extend(result.tools_used)
        if len(result.response) > len(best_response):
            best_response = result.response

    return {
        "report": best_response,
        "collateToolsUsed": list(dict.fromkeys(tools_used)),
        "turns": turns,
    }


class GDPRAnalysisInput(BaseModel):
    request: str = Field(
        description=(
            "The complete GDPR data-subject request, including identifiers, "
            "request type, and any scope or deadline supplied by the user."
        )
    )


class GDPRAnalysisTool(BaseTool):
    """Expose the AI Studio GDPR agent as one tool of our internal workflow."""

    name: str = "analyze_gdpr_request"
    description: str = (
        "Delegate a DSAR to Collate's governed GDPRComplianceAnalyzer. It searches "
        "the catalog, traces lineage, inspects PII, and evaluates retention conflicts."
    )
    args_schema: type[BaseModel] = GDPRAnalysisInput
    handle_tool_error: bool = True

    _agent: Any = PrivateAttr()

    def __init__(self, agent: Any, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._agent = agent

    def _run(
        self,
        request: str,
        run_manager: CallbackManagerForToolRun | None = None,
    ) -> str:
        del run_manager
        try:
            return json.dumps(_invoke_ai_studio_agent(self._agent, request))
        except Exception as exc:
            raise ToolException(f"AI Studio GDPR analysis failed: {exc}") from exc


class ExpertDirectoryInput(BaseModel):
    domain_hints: list[str] = Field(
        default_factory=list,
        description=(
            "Optional short Collate domain or data-product names. Pass [] to list "
            "all visible stewards and experts for application-side routing."
        ),
    )
    max_candidates: int = Field(
        default=20,
        ge=1,
        le=50,
        description="Maximum number of candidates to return.",
    )


class ExpertDirectoryTool(BaseTool):
    """Expose governed organizational context as an agent tool."""

    name: str = "find_data_stewards_and_experts"
    description: str = (
        "Read Collate's live users, Data Steward persona/role assignments, Domain "
        "experts, and Data Product experts to find evidence-backed handoff candidates."
    )
    args_schema: type[BaseModel] = ExpertDirectoryInput
    handle_tool_error: bool = True

    _directory: CollateExpertDirectory = PrivateAttr()

    def __init__(self, directory: CollateExpertDirectory, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._directory = directory

    def _run(
        self,
        domain_hints: list[str] | None = None,
        max_candidates: int = 20,
        run_manager: CallbackManagerForToolRun | None = None,
    ) -> str:
        del run_manager
        try:
            result = self._directory.find_candidates(
                domain_hints=domain_hints,
                max_candidates=max_candidates,
            )
            return json.dumps(result)
        except Exception as exc:
            raise ToolException(f"Collate expert discovery failed: {exc}") from exc


class GDPRWorkflowState(TypedDict, total=False):
    request: str
    compliance_report: str
    collate_tools_used: list[str]
    ai_studio_turns: int
    expert_context: dict[str, Any]
    response: str
    tools_used: Annotated[list[str], operator.add]
    execution: Annotated[list[dict[str, Any]], operator.add]


def _parse_tool_result(tool_name: str, result: Any) -> dict[str, Any]:
    if not isinstance(result, str):
        raise RuntimeError(f"{tool_name} returned a non-text result")
    try:
        parsed = json.loads(result)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{tool_name} failed: {result}") from exc
    if not isinstance(parsed, dict):
        raise RuntimeError(f"{tool_name} returned an invalid result")
    return parsed


def _execution_step(
    node: str,
    started_at: float,
    summary: str,
    details: list[str],
) -> dict[str, Any]:
    return {
        "node": node,
        "status": "completed",
        "durationMs": round((perf_counter() - started_at) * 1000),
        "summary": summary,
        "details": details,
    }


class GDPRHandoffWorkflow:
    """The explicit application workflow compiled by LangGraph."""

    def __init__(
        self,
        gdpr_tool: GDPRAnalysisTool,
        expert_tool: ExpertDirectoryTool,
        model: Any,
    ) -> None:
        self._gdpr_tool = gdpr_tool
        self._expert_tool = expert_tool
        self._model = model

        builder = StateGraph(GDPRWorkflowState)
        builder.add_node(
            "collate_gdpr_agent",
            self._run_collate_gdpr_agent,
            metadata={"owner": "collate", "responsibility": "compliance_analysis"},
        )
        builder.add_node(
            "collate_expert_directory",
            self._load_collate_experts,
            metadata={"owner": "shared", "responsibility": "organizational_context"},
        )
        builder.add_node(
            "internal_handoff_agent",
            self._run_internal_handoff_agent,
            metadata={"owner": "internal", "responsibility": "case_handoff"},
        )
        builder.add_edge(START, "collate_gdpr_agent")
        builder.add_edge("collate_gdpr_agent", "collate_expert_directory")
        builder.add_edge("collate_expert_directory", "internal_handoff_agent")
        builder.add_edge("internal_handoff_agent", END)
        self.graph = builder.compile()

    def _run_collate_gdpr_agent(
        self,
        state: GDPRWorkflowState,
        config: RunnableConfig,
    ) -> dict[str, Any]:
        started_at = perf_counter()
        payload = _parse_tool_result(
            self._gdpr_tool.name,
            self._gdpr_tool.invoke(
                {"request": state["request"]},
                config=config,
            ),
        )
        report = str(payload.get("report") or "")
        nested_tools = [str(name) for name in payload.get("collateToolsUsed") or []]
        turns = int(payload.get("turns") or 1)
        return {
            "compliance_report": report,
            "collate_tools_used": nested_tools,
            "ai_studio_turns": turns,
            "tools_used": [self._gdpr_tool.name],
            "execution": [
                _execution_step(
                    "collate_gdpr_agent",
                    started_at,
                    f"Produced a {len(report):,}-character report in {turns} turn(s)",
                    [
                        "AI Studio owns catalog search, asset context, lineage, PII, and retention reasoning.",
                        "Nested Collate tools: "
                        + (", ".join(nested_tools) or "none reported"),
                    ],
                )
            ],
        }

    def _load_collate_experts(
        self,
        state: GDPRWorkflowState,
        config: RunnableConfig,
    ) -> dict[str, Any]:
        del state
        started_at = perf_counter()
        context = _parse_tool_result(
            self._expert_tool.name,
            self._expert_tool.invoke(
                {"domain_hints": [], "max_candidates": 20},
                config=config,
            ),
        )
        candidates = context.get("candidates") or []
        counts = context.get("catalogCounts") or {}
        warnings = context.get("warnings") or []
        return {
            "expert_context": context,
            "tools_used": [self._expert_tool.name],
            "execution": [
                _execution_step(
                    "collate_expert_directory",
                    started_at,
                    f"Loaded {len(candidates)} visible handoff candidate(s)",
                    [
                        (
                            f"Catalog view: {counts.get('users', 0)} users, "
                            f"{counts.get('domains', 0)} domains, "
                            f"{counts.get('dataProducts', 0)} data products"
                        ),
                        f"Permission/API warnings: {len(warnings)}",
                    ],
                )
            ],
        }

    def _run_internal_handoff_agent(
        self,
        state: GDPRWorkflowState,
        config: RunnableConfig,
    ) -> dict[str, Any]:
        started_at = perf_counter()
        model_response = self._model.invoke(
            [
                SystemMessage(content=INTERNAL_AGENT_PROMPT),
                HumanMessage(
                    content=(
                        "ORIGINAL DSAR\n"
                        f"{state['request']}\n\n"
                        "AUTHORITATIVE AI STUDIO COMPLIANCE REPORT\n"
                        f"{state['compliance_report']}\n\n"
                        "LIVE COLLATE STEWARD/EXPERT CONTEXT (JSON)\n"
                        f"{json.dumps(state['expert_context'], indent=2)}"
                    )
                ),
            ],
            config=config,
        )
        handoff = _message_text(model_response.content).strip()
        report = state["compliance_report"].strip()
        response = f"## Compliance analysis\n\n{report}\n\n{handoff}"
        return {
            "response": response,
            "execution": [
                _execution_step(
                    "internal_handoff_agent",
                    started_at,
                    "Matched governed findings to people and prepared the human handoff",
                    [
                        "The internal model receives the report and directory result; it does not search the catalog.",
                        "The AI Studio compliance report is prepended unchanged.",
                    ],
                )
            ],
        }


@dataclass
class TraceRun:
    callbacks: list[Any]
    trace_url: str | None = None
    output: dict[str, Any] | None = None


class OptionalLangfuseTracing:
    """Opt-in Langfuse v4 tracing without making it a runtime requirement."""

    def __init__(self) -> None:
        requested = os.getenv("LANGFUSE_ENABLED", "").casefold() in {
            "1",
            "true",
            "yes",
            "on",
        }
        self.enabled = False
        self.status = "Disabled; set LANGFUSE_ENABLED=true to record traces"
        self._client: Any = None
        self._callback_type: Any = None
        self._propagate: Any = None

        if not requested:
            return
        if not os.getenv("LANGFUSE_PUBLIC_KEY") or not os.getenv("LANGFUSE_SECRET_KEY"):
            self.status = (
                "Disabled; LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY are required"
            )
            return

        try:
            from langfuse import get_client, propagate_attributes
            from langfuse.langchain import CallbackHandler
        except ImportError:
            self.status = "Disabled; install langfuse>=4 to record traces"
            return

        self._client = get_client()
        self._callback_type = CallbackHandler
        self._propagate = propagate_attributes
        self.enabled = True
        self.status = "Enabled; each run links to its Langfuse trace"

    @contextmanager
    def trace(self, request: str) -> Iterator[TraceRun]:
        if not self.enabled:
            yield TraceRun(callbacks=[])
            return

        try:
            with self._client.start_as_current_observation(
                as_type="agent",
                name="gdpr-handoff-workflow",
                input={"request": request},
            ) as observation:
                with self._propagate(
                    tags=["gdpr-demo", "langgraph", "collate"],
                    metadata={
                        "ai_studio_agent": AGENT_NAME,
                        "internal_model": MODEL,
                    },
                ):
                    trace_url = None
                    try:
                        trace_url = self._client.get_trace_url()
                    except Exception:
                        # The trace still works when its UI URL cannot be resolved.
                        pass
                    run = TraceRun(
                        callbacks=[self._callback_type()],
                        trace_url=trace_url,
                    )
                    try:
                        yield run
                    finally:
                        if run.output is not None:
                            observation.update(output=run.output)
        finally:
            # Make completed and failed traces visible promptly in the demo UI.
            self._flush()

    def _flush(self) -> None:
        try:
            self._client.flush()
        except Exception:
            # Observability must not turn a completed GDPR workflow into a failure.
            pass

    def close(self) -> None:
        if not self.enabled:
            return
        self._flush()
        shutdown = getattr(self._client, "shutdown", None)
        if callable(shutdown):
            shutdown()

    def description(self) -> dict[str, Any]:
        return {
            "provider": "Langfuse",
            "enabled": self.enabled,
            "status": self.status,
        }


class ExtendedGDPRRuntime:
    """Own the LangGraph workflow and its Collate-backed dependencies."""

    def __init__(self) -> None:
        config = AISdkConfig.from_env()
        self._sdk = AISdk.from_config(config)
        self._directory = CollateExpertDirectory(
            config.host,
            config.token,
            timeout=min(config.timeout, 60.0),
            verify_ssl=config.verify_ssl,
        )
        self._workflow = GDPRHandoffWorkflow(
            GDPRAnalysisTool(self._sdk.agent(AGENT_NAME)),
            ExpertDirectoryTool(self._directory),
            init_chat_model(MODEL),
        )
        self._tracing = OptionalLangfuseTracing()

    def graph_description(self) -> dict[str, Any]:
        return {
            "framework": "LangGraph",
            "nodes": WORKFLOW_NODES,
            "edges": WORKFLOW_EDGES,
            "mermaid": self._workflow.graph.get_graph().draw_mermaid(),
            "observability": self._tracing.description(),
        }

    def stream(self, request: str) -> Iterator[dict[str, Any]]:
        accumulated: dict[str, Any] = {
            "request": request,
            "tools_used": [],
            "execution": [],
        }

        with self._tracing.trace(request) as trace:
            graph_config: RunnableConfig = {
                "callbacks": trace.callbacks,
                "run_name": "gdpr-handoff-langgraph",
                "tags": ["gdpr-demo", "langgraph"],
                "metadata": {"ai_studio_agent": AGENT_NAME},
            }
            updates = self._workflow.graph.stream(
                {"request": request, "tools_used": [], "execution": []},
                config=graph_config,
                stream_mode="updates",
            )
            for update in updates:
                for node, values in update.items():
                    if not isinstance(values, dict):
                        continue
                    steps = values.get("execution") or []
                    accumulated["execution"].extend(steps)
                    accumulated["tools_used"].extend(values.get("tools_used") or [])
                    for key, value in values.items():
                        if key not in {"execution", "tools_used"}:
                            accumulated[key] = value
                    yield {
                        "type": "node",
                        "node": node,
                        "status": "completed",
                        "step": steps[-1] if steps else None,
                    }

            result = {
                "response": accumulated.get("response", ""),
                "toolsUsed": list(dict.fromkeys(accumulated["tools_used"])),
                "collateToolsUsed": accumulated.get("collate_tools_used", []),
                "execution": accumulated["execution"],
                "traceUrl": trace.trace_url,
            }
            trace.output = {
                "toolsUsed": result["toolsUsed"],
                "collateToolsUsed": result["collateToolsUsed"],
                "execution": result["execution"],
            }

        yield {"type": "result", **result}

    def analyze(self, request: str) -> dict[str, Any]:
        for event in self.stream(request):
            if event["type"] == "result":
                return {key: value for key, value in event.items() if key != "type"}
        raise RuntimeError("LangGraph finished without a result")

    def close(self) -> None:
        self._tracing.close()
        self._directory.close()
        self._sdk.close()


def _message_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("text"):
                parts.append(str(block["text"]))
        return "\n".join(parts)
    return str(content)


class DemoHandler(BaseHTTPRequestHandler):
    runtime: ExtendedGDPRRuntime

    def _json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _request_message(self) -> str:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > 64 * 1024:
            raise ValueError("Request body must be between 1 byte and 64 KiB")
        payload = json.loads(self.rfile.read(length))
        message = payload.get("message") if isinstance(payload, dict) else None
        if not isinstance(message, str) or not message.strip():
            raise ValueError("'message' must be a non-empty string")
        return message.strip()

    def _stream_event(self, payload: dict[str, Any]) -> None:
        self.wfile.write(json.dumps(payload).encode("utf-8") + b"\n")
        self.wfile.flush()

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/api/config":
            self._json(
                HTTPStatus.OK,
                {
                    "runtimeLabel": "LangGraph · AI Studio + Collate experts",
                    "responseTitle": "Compliance & Handoff Plan",
                    "workingLabel": "LangGraph is running the governed handoff...",
                    "streamEndpoint": "/api/analyze/stream",
                    "observability": self.runtime.graph_description()["observability"],
                },
            )
            return
        if self.path == "/api/graph":
            self._json(HTTPStatus.OK, self.runtime.graph_description())
            return
        if self.path not in ("/", "/index.html"):
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        body = FRONTEND.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802
        if self.path not in ("/api/analyze", "/api/analyze/stream"):
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            message = self._request_message()
        except (ValueError, json.JSONDecodeError) as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if self.path == "/api/analyze/stream":
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "close")
            self.end_headers()
            try:
                for event in self.runtime.stream(message):
                    self._stream_event(event)
            except Exception as exc:
                self._stream_event({"type": "error", "error": str(exc)})
            return

        try:
            self._json(HTTPStatus.OK, self.runtime.analyze(message))
        except Exception as exc:
            self._json(HTTPStatus.BAD_GATEWAY, {"error": str(exc)})


def main() -> None:
    runtime = ExtendedGDPRRuntime()
    DemoHandler.runtime = runtime
    server = ThreadingHTTPServer(("127.0.0.1", PORT), DemoHandler)
    print(f"Extended GDPR demo -> http://localhost:{PORT}")
    print(f"Workflow: LangGraph -> {len(WORKFLOW_NODES)} visible nodes")
    print(f"Internal agent: {MODEL}")
    print(f"Collate agent: {AGENT_NAME}")
    print(f"Observability: {runtime.graph_description()['observability']['status']}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        server.server_close()
        runtime.close()


if __name__ == "__main__":
    main()
