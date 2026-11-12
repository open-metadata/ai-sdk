"""Check SDK contracts against Git revisions of OpenMetadata and Collate.

Run with the SDK installed, or set PYTHONPATH=python/src. No server is required.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

from ai_sdk._streaming import SSEIterator
from ai_sdk.api.memories import _build_list_params
from ai_sdk.mcp._openai import build_openai_tools
from ai_sdk.mcp.models import MCPTool, ToolInfo
from ai_sdk.models import (
    ContextMemory,
    CreateAgentRequest,
    CreateContextMemoryRequest,
    InvokeRequest,
    InvokeResponse,
    MemoryStatus,
    MemoryType,
    MemoryVisibility,
)


def read(repo: Path, revision: str, path: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), "show", f"{revision}:{path}"], text=True
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--openmetadata", type=Path, required=True)
    parser.add_argument("--collate", type=Path, required=True)
    parser.add_argument("--openmetadata-ref", default="origin/main")
    parser.add_argument("--collate-ref", default="origin/main")
    args = parser.parse_args()
    oss_schema = "openmetadata-spec/src/main/resources/json/schema/"
    collate_schema = "collate-service/src/main/resources/json/schema/"

    def oss(path: str) -> dict:
        return json.loads(
            read(args.openmetadata, args.openmetadata_ref, oss_schema + path)
        )

    def collate(path: str) -> dict:
        return json.loads(read(args.collate, args.collate_ref, collate_schema + path))

    memory = oss("entity/context/contextMemory.json")
    for model, definition in [
        (MemoryType, "memoryType"),
        (MemoryVisibility, "shareVisibility"),
    ]:
        assert {item.value for item in model} == set(
            memory["definitions"][definition]["enum"]
        )
    assert {item.value for item in MemoryStatus} == set(
        oss("entity/context/contextMemoryStatus.json")["enum"]
    )
    for stage in MemoryStatus:
        parsed = ContextMemory.from_dict(
            {"id": "m1", "name": "m", "entityStatus": stage.value}
        )
        assert parsed.entity_status == stage
    created = CreateContextMemoryRequest(
        name="m", question="q", answer="a", entity_status="Approved"
    )
    assert set(created.to_api_dict()) <= set(
        oss("api/context/createContextMemory.json")["properties"]
    )

    agent = collate("entity/ai/dynamicAgent.json")
    modes = set(agent["definitions"]["agentMode"]["enum"])
    assert (
        set(CreateAgentRequest.model_json_schema()["properties"]["mode"]["enum"])
        == modes
    )
    for mode in modes:
        request = CreateAgentRequest(
            name="agent",
            description="d",
            persona="p",
            mode=mode,
            planner_description={
                "description": "d",
                "input": "i",
                "output": "o",
                "prompt": "work",
            },
        )
        assert set(request.to_api_dict()) <= set(
            collate("api/ai/createDynamicAgent.json")["properties"]
        )
    assert set(collate("api/agent/invokeAgentRequest.json")["required"]) <= set(
        InvokeRequest().to_api_dict()
    )

    resource = read(
        args.openmetadata,
        args.openmetadata_ref,
        "openmetadata-service/src/main/java/org/openmetadata/service/resources/context/ContextMemoryResource.java",
    )
    bound_params = set(re.findall(r'@QueryParam\("([^\"]+)"\)', resource))
    assert set(_build_list_params("asset-id", None, 100)) <= bound_params

    tools = []
    for repo, revision, path in [
        (
            args.openmetadata,
            args.openmetadata_ref,
            "openmetadata-mcp/src/main/resources/json/data/mcp/tools.json",
        ),
        (
            args.collate,
            args.collate_ref,
            "collate-mcp/src/main/resources/json/data/mcp/collateTools.json",
        ),
    ]:
        tools.extend(json.loads(read(repo, revision, path))["tools"])
    assert {tool.value for tool in MCPTool} == {tool["name"] for tool in tools}
    for tool in tools:
        info = ToolInfo(tool["name"], tool.get("description", ""), tool["parameters"])
        assert (
            build_openai_tools([info])[0]["function"]["parameters"]
            == tool["parameters"]
        )

    executor = read(
        args.collate,
        args.collate_ref,
        "collate-service/src/main/java/io/collate/util/grpc/GRPCExecutor.java",
    )
    assert '.name("stream-error")' in executor
    event = next(
        iter(
            SSEIterator(iter([b'event: stream-error\ndata: {"message":"failed"}\n\n']))
        )
    )
    assert event.type == "error" and event.error == "failed"
    components = [{"type": "chart", "content": {"title": "Revenue"}}]
    assert "components" in collate("api/agent/invokeAgentResponse.json")["properties"]
    assert (
        InvokeResponse(
            conversation_id="c1", response="", components=components
        ).components
        == components
    )

    for repo, revision in [
        (args.openmetadata, args.openmetadata_ref),
        (args.collate, args.collate_ref),
    ]:
        commit = subprocess.check_output(
            ["git", "-C", str(repo), "rev-parse", revision], text=True
        ).strip()
        print(f"{repo.name}: {commit}")
    print("SDK request, response, MCP schema, and streaming contracts match.")


if __name__ == "__main__":
    main()
