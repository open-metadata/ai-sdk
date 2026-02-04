# MCP Tools Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add MCP tool support to the Python SDK, enabling users to expose OpenMetadata's MCP tools to LangChain and OpenAI-compatible AI frameworks.

**Architecture:** The SDK will communicate with OpenMetadata's MCP server via JSON-RPC 2.0 over HTTP. Tool definitions are fetched dynamically and converted to framework-specific formats. An `MCPTool` enum provides type-safe tool selection.

**Tech Stack:** Python 3.10+, httpx (existing), pydantic (existing), langchain-core (optional)

---

## Task 1: Create MCP Models

**Files:**
- Create: `python/src/metadata_ai/mcp/__init__.py`
- Create: `python/src/metadata_ai/mcp/_models.py`
- Test: `python/tests/test_mcp_models.py`

**Step 1: Create the mcp package directory**

```bash
mkdir -p python/src/metadata_ai/mcp
```

**Step 2: Create empty `__init__.py`**

Create `python/src/metadata_ai/mcp/__init__.py`:

```python
"""MCP (Model Context Protocol) integration for OpenMetadata tools."""
```

**Step 3: Write the failing test for MCPTool enum**

Create `python/tests/test_mcp_models.py`:

```python
"""Tests for MCP models."""

from metadata_ai.mcp._models import MCPTool


class TestMCPToolEnum:
    """Tests for MCPTool enum."""

    def test_enum_has_all_tools(self):
        """MCPTool enum contains all expected tools."""
        assert MCPTool.SEARCH_METADATA == "search_metadata"
        assert MCPTool.GET_ENTITY_DETAILS == "get_entity_details"
        assert MCPTool.GET_ENTITY_LINEAGE == "get_entity_lineage"
        assert MCPTool.CREATE_GLOSSARY == "create_glossary"
        assert MCPTool.CREATE_GLOSSARY_TERM == "create_glossary_term"
        assert MCPTool.PATCH_ENTITY == "patch_entity"

    def test_enum_is_str_enum(self):
        """MCPTool values are strings."""
        for tool in MCPTool:
            assert isinstance(tool.value, str)
            assert isinstance(tool, str)
```

**Step 4: Run test to verify it fails**

```bash
cd python && pytest tests/test_mcp_models.py -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'metadata_ai.mcp'"

**Step 5: Write MCPTool enum**

Create `python/src/metadata_ai/mcp/_models.py`:

```python
"""Models for MCP integration."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class MCPTool(StrEnum):
    """Available MCP tools from OpenMetadata."""

    SEARCH_METADATA = "search_metadata"
    GET_ENTITY_DETAILS = "get_entity_details"
    GET_ENTITY_LINEAGE = "get_entity_lineage"
    CREATE_GLOSSARY = "create_glossary"
    CREATE_GLOSSARY_TERM = "create_glossary_term"
    PATCH_ENTITY = "patch_entity"
```

**Step 6: Run test to verify it passes**

```bash
cd python && pytest tests/test_mcp_models.py::TestMCPToolEnum -v
```

Expected: PASS

**Step 7: Write failing test for ToolParameter**

Add to `python/tests/test_mcp_models.py`:

```python
from metadata_ai.mcp._models import MCPTool, ToolParameter, ToolInfo, ToolCallResult


class TestToolParameter:
    """Tests for ToolParameter dataclass."""

    def test_create_tool_parameter(self):
        """ToolParameter can be created with all fields."""
        param = ToolParameter(
            name="query",
            type="string",
            description="Search query",
            required=True,
        )
        assert param.name == "query"
        assert param.type == "string"
        assert param.description == "Search query"
        assert param.required is True

    def test_optional_parameter(self):
        """ToolParameter handles optional parameters."""
        param = ToolParameter(
            name="size",
            type="integer",
            description="Page size",
            required=False,
        )
        assert param.required is False
```

**Step 8: Run test to verify it fails**

```bash
cd python && pytest tests/test_mcp_models.py::TestToolParameter -v
```

Expected: FAIL with "cannot import name 'ToolParameter'"

**Step 9: Write ToolParameter dataclass**

Add to `python/src/metadata_ai/mcp/_models.py`:

```python
@dataclass
class ToolParameter:
    """Schema for a tool parameter."""

    name: str
    type: str  # "string", "integer", "boolean", "array", "object"
    description: str
    required: bool
```

**Step 10: Run test to verify it passes**

```bash
cd python && pytest tests/test_mcp_models.py::TestToolParameter -v
```

Expected: PASS

**Step 11: Write failing test for ToolInfo**

Add to `python/tests/test_mcp_models.py`:

```python
class TestToolInfo:
    """Tests for ToolInfo dataclass."""

    def test_create_tool_info(self):
        """ToolInfo can be created with all fields."""
        params = [
            ToolParameter(name="query", type="string", description="Search", required=True),
        ]
        info = ToolInfo(
            name=MCPTool.SEARCH_METADATA,
            description="Search metadata catalog",
            parameters=params,
        )
        assert info.name == MCPTool.SEARCH_METADATA
        assert info.description == "Search metadata catalog"
        assert len(info.parameters) == 1
```

**Step 12: Run test to verify it fails**

```bash
cd python && pytest tests/test_mcp_models.py::TestToolInfo -v
```

Expected: FAIL

**Step 13: Write ToolInfo dataclass**

Add to `python/src/metadata_ai/mcp/_models.py`:

```python
@dataclass
class ToolInfo:
    """Metadata about an MCP tool."""

    name: MCPTool
    description: str
    parameters: list[ToolParameter]
```

**Step 14: Run test to verify it passes**

```bash
cd python && pytest tests/test_mcp_models.py::TestToolInfo -v
```

Expected: PASS

**Step 15: Write failing test for ToolCallResult**

Add to `python/tests/test_mcp_models.py`:

```python
class TestToolCallResult:
    """Tests for ToolCallResult dataclass."""

    def test_successful_result(self):
        """ToolCallResult represents success."""
        result = ToolCallResult(
            success=True,
            data={"tables": [{"name": "customers"}]},
            error=None,
        )
        assert result.success is True
        assert result.data == {"tables": [{"name": "customers"}]}
        assert result.error is None

    def test_error_result(self):
        """ToolCallResult represents error."""
        result = ToolCallResult(
            success=False,
            data=None,
            error="Tool execution failed",
        )
        assert result.success is False
        assert result.data is None
        assert result.error == "Tool execution failed"
```

**Step 16: Run test to verify it fails**

```bash
cd python && pytest tests/test_mcp_models.py::TestToolCallResult -v
```

Expected: FAIL

**Step 17: Write ToolCallResult dataclass**

Add to `python/src/metadata_ai/mcp/_models.py`:

```python
@dataclass
class ToolCallResult:
    """Result from calling an MCP tool."""

    success: bool
    data: dict | None
    error: str | None
```

**Step 18: Run all model tests**

```bash
cd python && pytest tests/test_mcp_models.py -v
```

Expected: All PASS

**Step 19: Commit**

```bash
git add python/src/metadata_ai/mcp/ python/tests/test_mcp_models.py
git commit -m "feat(mcp): add MCP models - MCPTool enum, ToolParameter, ToolInfo, ToolCallResult"
```

---

## Task 2: Add MCP Exceptions

**Files:**
- Modify: `python/src/metadata_ai/exceptions.py`
- Test: `python/tests/test_mcp_models.py` (extend)

**Step 1: Write failing test for MCP exceptions**

Add to `python/tests/test_mcp_models.py`:

```python
from metadata_ai.exceptions import MCPError, MCPToolExecutionError


class TestMCPExceptions:
    """Tests for MCP-specific exceptions."""

    def test_mcp_error_base(self):
        """MCPError is base exception."""
        error = MCPError("Something went wrong")
        assert str(error) == "Something went wrong"
        assert error.status_code is None

    def test_mcp_tool_execution_error(self):
        """MCPToolExecutionError includes tool name."""
        error = MCPToolExecutionError(MCPTool.SEARCH_METADATA, "Connection failed")
        assert "search_metadata" in str(error)
        assert "Connection failed" in str(error)
        assert error.tool == MCPTool.SEARCH_METADATA
```

**Step 2: Run test to verify it fails**

```bash
cd python && pytest tests/test_mcp_models.py::TestMCPExceptions -v
```

Expected: FAIL with "cannot import name 'MCPError'"

**Step 3: Add MCP exceptions to exceptions.py**

Add to `python/src/metadata_ai/exceptions.py` at the end:

```python
class MCPError(MetadataError):
    """Base error for MCP operations."""

    pass


class MCPToolExecutionError(MCPError):
    """Tool execution failed."""

    def __init__(self, tool: str, message: str) -> None:
        self.tool = tool
        super().__init__(f"Tool '{tool}' failed: {message}")
```

**Step 4: Run test to verify it passes**

```bash
cd python && pytest tests/test_mcp_models.py::TestMCPExceptions -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add python/src/metadata_ai/exceptions.py python/tests/test_mcp_models.py
git commit -m "feat(mcp): add MCPError and MCPToolExecutionError exceptions"
```

---

## Task 3: Create MCP Client Core

**Files:**
- Create: `python/src/metadata_ai/mcp/_client.py`
- Test: `python/tests/test_mcp_client.py`

**Step 1: Write failing test for MCPClient initialization**

Create `python/tests/test_mcp_client.py`:

```python
"""Tests for MCP client."""

import json

import pytest
from pytest_httpx import HTTPXMock

from metadata_ai.client import MetadataAI
from metadata_ai.mcp._client import MCPClient
from metadata_ai.mcp._models import MCPTool, ToolInfo


@pytest.fixture
def client():
    """MetadataAI client fixture."""
    c = MetadataAI(
        host="https://metadata.example.com",
        token="test-token",
        max_retries=0,
    )
    yield c
    c.close()


class TestMCPClientInit:
    """Tests for MCPClient initialization."""

    def test_mcp_client_created_from_metadata_client(self, client):
        """MCPClient can be created from MetadataAI client."""
        mcp = MCPClient(client._host, client._auth, client._http)
        assert mcp is not None
```

**Step 2: Run test to verify it fails**

```bash
cd python && pytest tests/test_mcp_client.py::TestMCPClientInit -v
```

Expected: FAIL with "cannot import name 'MCPClient'"

**Step 3: Write MCPClient skeleton**

Create `python/src/metadata_ai/mcp/_client.py`:

```python
"""MCP client for OpenMetadata's MCP server."""

from __future__ import annotations

import json
import uuid
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from metadata_ai._http import HTTPClient
    from metadata_ai.auth import TokenAuth

from metadata_ai.exceptions import MCPError, MCPToolExecutionError
from metadata_ai.mcp._models import MCPTool, ToolCallResult, ToolInfo, ToolParameter


class MCPClient:
    """Client for OpenMetadata's MCP server."""

    def __init__(
        self,
        host: str,
        auth: TokenAuth,
        http: HTTPClient,
    ) -> None:
        """
        Initialize the MCP client.

        Args:
            host: OpenMetadata server host URL
            auth: Authentication handler
            http: HTTP client for making requests
        """
        self._host = host.rstrip("/")
        self._auth = auth
        self._http = http
        self._mcp_endpoint = f"{self._host}/mcp"
```

**Step 4: Run test to verify it passes**

```bash
cd python && pytest tests/test_mcp_client.py::TestMCPClientInit -v
```

Expected: PASS

**Step 5: Write failing test for list_tools**

Add to `python/tests/test_mcp_client.py`:

```python
class TestMCPClientListTools:
    """Tests for MCPClient.list_tools()."""

    def test_list_tools_returns_tool_info_list(self, client, httpx_mock: HTTPXMock):
        """list_tools returns list of ToolInfo."""
        httpx_mock.add_response(
            url="https://metadata.example.com/mcp",
            method="POST",
            json={
                "jsonrpc": "2.0",
                "id": "test-id",
                "result": {
                    "tools": [
                        {
                            "name": "search_metadata",
                            "description": "Search for metadata",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query": {
                                        "type": "string",
                                        "description": "Search query",
                                    },
                                },
                                "required": ["query"],
                            },
                        },
                    ]
                },
            },
        )

        mcp = MCPClient(client._host, client._auth, client._http)
        tools = mcp.list_tools()

        assert len(tools) == 1
        assert tools[0].name == MCPTool.SEARCH_METADATA
        assert tools[0].description == "Search for metadata"
        assert len(tools[0].parameters) == 1
        assert tools[0].parameters[0].name == "query"
        assert tools[0].parameters[0].required is True
```

**Step 6: Run test to verify it fails**

```bash
cd python && pytest tests/test_mcp_client.py::TestMCPClientListTools -v
```

Expected: FAIL with "AttributeError: 'MCPClient' object has no attribute 'list_tools'"

**Step 7: Implement list_tools method**

Add to `python/src/metadata_ai/mcp/_client.py` in MCPClient class:

```python
    def _make_jsonrpc_request(self, method: str, params: dict | None = None) -> dict:
        """Make a JSON-RPC 2.0 request to the MCP server."""
        request_id = str(uuid.uuid4())[:8]
        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {},
        }

        # Use httpx directly since MCP endpoint is different from agent API
        import httpx

        headers = {"Authorization": f"Bearer {self._auth.token}"}
        response = httpx.post(
            self._mcp_endpoint,
            json=payload,
            headers=headers,
            timeout=30.0,
        )

        if response.status_code != 200:
            raise MCPError(f"MCP request failed: {response.text}", status_code=response.status_code)

        result = response.json()
        if "error" in result:
            raise MCPError(f"MCP error: {result['error'].get('message', 'Unknown error')}")

        return result.get("result", {})

    def list_tools(self) -> list[ToolInfo]:
        """
        Fetch available tools from MCP server.

        Returns:
            List of ToolInfo describing available tools
        """
        result = self._make_jsonrpc_request("tools/list")
        tools_data = result.get("tools", [])
        return [self._parse_tool_info(t) for t in tools_data]

    def _parse_tool_info(self, data: dict) -> ToolInfo:
        """Parse tool info from MCP response."""
        name = MCPTool(data["name"])
        description = data.get("description", "")
        parameters = self._parse_parameters(data.get("inputSchema", {}))
        return ToolInfo(name=name, description=description, parameters=parameters)

    def _parse_parameters(self, schema: dict) -> list[ToolParameter]:
        """Parse parameters from JSON schema."""
        if schema.get("type") != "object":
            return []

        properties = schema.get("properties", {})
        required = set(schema.get("required", []))
        parameters = []

        for name, prop in properties.items():
            parameters.append(
                ToolParameter(
                    name=name,
                    type=prop.get("type", "string"),
                    description=prop.get("description", ""),
                    required=name in required,
                )
            )

        return parameters
```

**Step 8: Run test to verify it passes**

```bash
cd python && pytest tests/test_mcp_client.py::TestMCPClientListTools -v
```

Expected: PASS

**Step 9: Write failing test for call_tool**

Add to `python/tests/test_mcp_client.py`:

```python
class TestMCPClientCallTool:
    """Tests for MCPClient.call_tool()."""

    def test_call_tool_returns_result(self, client, httpx_mock: HTTPXMock):
        """call_tool returns ToolCallResult on success."""
        httpx_mock.add_response(
            url="https://metadata.example.com/mcp",
            method="POST",
            json={
                "jsonrpc": "2.0",
                "id": "test-id",
                "result": {
                    "content": [
                        {"type": "text", "text": '{"tables": ["customers"]}'}
                    ]
                },
            },
        )

        mcp = MCPClient(client._host, client._auth, client._http)
        result = mcp.call_tool(MCPTool.SEARCH_METADATA, {"query": "customer"})

        assert result.success is True
        assert result.data is not None
        assert result.error is None

    def test_call_tool_handles_error(self, client, httpx_mock: HTTPXMock):
        """call_tool returns error result on failure."""
        httpx_mock.add_response(
            url="https://metadata.example.com/mcp",
            method="POST",
            json={
                "jsonrpc": "2.0",
                "id": "test-id",
                "error": {
                    "code": -32000,
                    "message": "Tool execution failed",
                },
            },
        )

        mcp = MCPClient(client._host, client._auth, client._http)

        with pytest.raises(MCPError) as exc_info:
            mcp.call_tool(MCPTool.SEARCH_METADATA, {"query": "test"})

        assert "Tool execution failed" in str(exc_info.value)
```

**Step 10: Run test to verify it fails**

```bash
cd python && pytest tests/test_mcp_client.py::TestMCPClientCallTool -v
```

Expected: FAIL with "AttributeError: 'MCPClient' object has no attribute 'call_tool'"

**Step 11: Implement call_tool method**

Add to `python/src/metadata_ai/mcp/_client.py` in MCPClient class:

```python
    def call_tool(self, name: MCPTool, arguments: dict) -> ToolCallResult:
        """
        Execute a tool via MCP protocol.

        Args:
            name: Tool to call (from MCPTool enum)
            arguments: Tool arguments as dictionary

        Returns:
            ToolCallResult with success/error info
        """
        result = self._make_jsonrpc_request(
            "tools/call",
            {"name": name.value, "arguments": arguments},
        )

        # Parse MCP tool result
        content = result.get("content", [])
        if content and len(content) > 0:
            first_content = content[0]
            if first_content.get("type") == "text":
                text = first_content.get("text", "{}")
                data = json.loads(text) if text.startswith("{") else {"text": text}
                return ToolCallResult(success=True, data=data, error=None)

        return ToolCallResult(success=True, data={}, error=None)
```

**Step 12: Run test to verify it passes**

```bash
cd python && pytest tests/test_mcp_client.py::TestMCPClientCallTool -v
```

Expected: PASS

**Step 13: Run all MCP client tests**

```bash
cd python && pytest tests/test_mcp_client.py -v
```

Expected: All PASS

**Step 14: Commit**

```bash
git add python/src/metadata_ai/mcp/_client.py python/tests/test_mcp_client.py
git commit -m "feat(mcp): add MCPClient with list_tools and call_tool methods"
```

---

## Task 4: Add mcp Property to MetadataAI Client

**Files:**
- Modify: `python/src/metadata_ai/client.py`
- Test: `python/tests/test_mcp_client.py` (extend)

**Step 1: Write failing test for client.mcp property**

Add to `python/tests/test_mcp_client.py`:

```python
class TestMetadataAIMCPProperty:
    """Tests for MetadataAI.mcp property."""

    def test_mcp_property_returns_mcp_client(self, client):
        """MetadataAI.mcp returns MCPClient instance."""
        mcp = client.mcp
        assert isinstance(mcp, MCPClient)

    def test_mcp_property_is_cached(self, client):
        """MetadataAI.mcp returns same instance on repeated access."""
        mcp1 = client.mcp
        mcp2 = client.mcp
        assert mcp1 is mcp2
```

**Step 2: Run test to verify it fails**

```bash
cd python && pytest tests/test_mcp_client.py::TestMetadataAIMCPProperty -v
```

Expected: FAIL with "AttributeError: 'MetadataAI' object has no attribute 'mcp'"

**Step 3: Add mcp property to MetadataAI**

Add import at top of `python/src/metadata_ai/client.py`:

```python
from metadata_ai.mcp._client import MCPClient
```

Add to `MetadataAI.__init__` after other client initializations:

```python
        self._mcp_client: MCPClient | None = None
```

Add property to `MetadataAI` class:

```python
    @property
    def mcp(self) -> MCPClient:
        """
        Get the MCP client for tool operations.

        Returns:
            MCPClient instance for interacting with OpenMetadata's MCP server

        Example:
            tools = client.mcp.list_tools()
            result = client.mcp.call_tool(MCPTool.SEARCH_METADATA, {"query": "customer"})
        """
        if self._mcp_client is None:
            self._mcp_client = MCPClient(
                host=self._host,
                auth=self._auth,
                http=self._http,
            )
        return self._mcp_client
```

**Step 4: Run test to verify it passes**

```bash
cd python && pytest tests/test_mcp_client.py::TestMetadataAIMCPProperty -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add python/src/metadata_ai/client.py python/tests/test_mcp_client.py
git commit -m "feat(mcp): add mcp property to MetadataAI client"
```

---

## Task 5: Add Tool Filtering to MCPClient

**Files:**
- Modify: `python/src/metadata_ai/mcp/_client.py`
- Test: `python/tests/test_mcp_client.py` (extend)

**Step 1: Write failing test for filter_tools helper**

Add to `python/tests/test_mcp_client.py`:

```python
from metadata_ai.mcp._models import MCPTool, ToolInfo, ToolParameter


class TestMCPClientFiltering:
    """Tests for tool filtering."""

    @pytest.fixture
    def sample_tools(self):
        """Sample ToolInfo list."""
        return [
            ToolInfo(
                name=MCPTool.SEARCH_METADATA,
                description="Search",
                parameters=[],
            ),
            ToolInfo(
                name=MCPTool.GET_ENTITY_DETAILS,
                description="Get entity",
                parameters=[],
            ),
            ToolInfo(
                name=MCPTool.PATCH_ENTITY,
                description="Patch entity",
                parameters=[],
            ),
        ]

    def test_filter_tools_include(self, sample_tools):
        """filter_tools with include returns only specified tools."""
        from metadata_ai.mcp._client import _filter_tools

        filtered = _filter_tools(
            sample_tools,
            include=[MCPTool.SEARCH_METADATA],
            exclude=None,
        )

        assert len(filtered) == 1
        assert filtered[0].name == MCPTool.SEARCH_METADATA

    def test_filter_tools_exclude(self, sample_tools):
        """filter_tools with exclude removes specified tools."""
        from metadata_ai.mcp._client import _filter_tools

        filtered = _filter_tools(
            sample_tools,
            include=None,
            exclude=[MCPTool.PATCH_ENTITY],
        )

        assert len(filtered) == 2
        tool_names = [t.name for t in filtered]
        assert MCPTool.PATCH_ENTITY not in tool_names

    def test_filter_tools_none_returns_all(self, sample_tools):
        """filter_tools with no filters returns all tools."""
        from metadata_ai.mcp._client import _filter_tools

        filtered = _filter_tools(sample_tools, include=None, exclude=None)

        assert len(filtered) == 3
```

**Step 2: Run test to verify it fails**

```bash
cd python && pytest tests/test_mcp_client.py::TestMCPClientFiltering -v
```

Expected: FAIL with "cannot import name '_filter_tools'"

**Step 3: Implement _filter_tools function**

Add to `python/src/metadata_ai/mcp/_client.py` before MCPClient class:

```python
def _filter_tools(
    tools: list[ToolInfo],
    include: list[MCPTool] | None,
    exclude: list[MCPTool] | None,
) -> list[ToolInfo]:
    """
    Filter tools by include/exclude lists.

    Args:
        tools: List of ToolInfo to filter
        include: If provided, only include these tools
        exclude: If provided, exclude these tools

    Returns:
        Filtered list of ToolInfo
    """
    if include is not None:
        include_set = set(include)
        tools = [t for t in tools if t.name in include_set]

    if exclude is not None:
        exclude_set = set(exclude)
        tools = [t for t in tools if t.name not in exclude_set]

    return tools
```

**Step 4: Run test to verify it passes**

```bash
cd python && pytest tests/test_mcp_client.py::TestMCPClientFiltering -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add python/src/metadata_ai/mcp/_client.py python/tests/test_mcp_client.py
git commit -m "feat(mcp): add tool filtering helper function"
```

---

## Task 6: Create OpenAI Adapter

**Files:**
- Create: `python/src/metadata_ai/mcp/_openai.py`
- Test: `python/tests/test_mcp_openai.py`

**Step 1: Write failing test for as_openai_tools**

Create `python/tests/test_mcp_openai.py`:

```python
"""Tests for MCP OpenAI adapter."""

import pytest
from pytest_httpx import HTTPXMock

from metadata_ai.client import MetadataAI
from metadata_ai.mcp._models import MCPTool


@pytest.fixture
def client():
    """MetadataAI client fixture."""
    c = MetadataAI(
        host="https://metadata.example.com",
        token="test-token",
        max_retries=0,
    )
    yield c
    c.close()


@pytest.fixture
def mock_list_tools(httpx_mock: HTTPXMock):
    """Mock list_tools response."""
    httpx_mock.add_response(
        url="https://metadata.example.com/mcp",
        method="POST",
        json={
            "jsonrpc": "2.0",
            "id": "test",
            "result": {
                "tools": [
                    {
                        "name": "search_metadata",
                        "description": "Search for metadata in the catalog",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string", "description": "Search query"},
                                "size": {"type": "integer", "description": "Result count"},
                            },
                            "required": ["query"],
                        },
                    },
                ]
            },
        },
    )


class TestAsOpenAITools:
    """Tests for MCPClient.as_openai_tools()."""

    def test_returns_openai_function_schema(self, client, mock_list_tools):
        """as_openai_tools returns OpenAI function calling format."""
        tools = client.mcp.as_openai_tools()

        assert len(tools) == 1
        tool = tools[0]

        assert tool["type"] == "function"
        assert tool["function"]["name"] == "search_metadata"
        assert tool["function"]["description"] == "Search for metadata in the catalog"
        assert tool["function"]["parameters"]["type"] == "object"
        assert "query" in tool["function"]["parameters"]["properties"]
        assert "query" in tool["function"]["parameters"]["required"]

    def test_filters_tools_with_include(self, client, httpx_mock: HTTPXMock):
        """as_openai_tools filters with include parameter."""
        httpx_mock.add_response(
            url="https://metadata.example.com/mcp",
            method="POST",
            json={
                "jsonrpc": "2.0",
                "id": "test",
                "result": {
                    "tools": [
                        {"name": "search_metadata", "description": "Search", "inputSchema": {}},
                        {"name": "patch_entity", "description": "Patch", "inputSchema": {}},
                    ]
                },
            },
        )

        tools = client.mcp.as_openai_tools(include=[MCPTool.SEARCH_METADATA])

        assert len(tools) == 1
        assert tools[0]["function"]["name"] == "search_metadata"
```

**Step 2: Run test to verify it fails**

```bash
cd python && pytest tests/test_mcp_openai.py -v
```

Expected: FAIL with "AttributeError: 'MCPClient' object has no attribute 'as_openai_tools'"

**Step 3: Create OpenAI adapter module**

Create `python/src/metadata_ai/mcp/_openai.py`:

```python
"""OpenAI function calling adapter for MCP tools."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from metadata_ai.mcp._client import MCPClient

from metadata_ai.mcp._models import MCPTool, ToolInfo


def build_openai_tools(
    tools: list[ToolInfo],
) -> list[dict]:
    """
    Convert ToolInfo list to OpenAI function calling format.

    Args:
        tools: List of ToolInfo from MCP server

    Returns:
        List of dicts in OpenAI function calling schema format
    """
    return [_to_openai_schema(info) for info in tools]


def _to_openai_schema(info: ToolInfo) -> dict:
    """Convert single ToolInfo to OpenAI function schema."""
    properties = {}
    required = []

    for param in info.parameters:
        properties[param.name] = {
            "type": param.type,
            "description": param.description,
        }
        if param.required:
            required.append(param.name)

    return {
        "type": "function",
        "function": {
            "name": info.name.value,
            "description": info.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        },
    }


def create_tool_executor(mcp_client: MCPClient):
    """
    Create executor function for OpenAI tool calls.

    Args:
        mcp_client: MCPClient instance

    Returns:
        Callable that executes tool calls
    """

    def execute(tool_name: str, arguments: dict) -> dict:
        tool = MCPTool(tool_name)
        result = mcp_client.call_tool(tool, arguments)
        if not result.success:
            return {"error": result.error}
        return result.data or {}

    return execute
```

**Step 4: Add as_openai_tools method to MCPClient**

Add to `python/src/metadata_ai/mcp/_client.py` in MCPClient class:

```python
    def as_openai_tools(
        self,
        include: list[MCPTool] | None = None,
        exclude: list[MCPTool] | None = None,
    ) -> list[dict]:
        """
        Get tools formatted for OpenAI function calling.

        Args:
            include: Only include these tools (allowlist)
            exclude: Exclude these tools (blocklist)

        Returns:
            List of dicts in OpenAI function calling schema format
        """
        from metadata_ai.mcp._openai import build_openai_tools

        tools = self.list_tools()
        filtered = _filter_tools(tools, include, exclude)
        return build_openai_tools(filtered)

    def create_tool_executor(self):
        """
        Create executor function for OpenAI tool calls.

        Returns:
            Callable[[str, dict], dict] that executes tool calls

        Example:
            tools = client.mcp.as_openai_tools()
            executor = client.mcp.create_tool_executor()

            # After OpenAI returns a tool call
            result = executor(tool_call.function.name, arguments)
        """
        from metadata_ai.mcp._openai import create_tool_executor

        return create_tool_executor(self)
```

**Step 5: Run test to verify it passes**

```bash
cd python && pytest tests/test_mcp_openai.py -v
```

Expected: PASS

**Step 6: Commit**

```bash
git add python/src/metadata_ai/mcp/_openai.py python/src/metadata_ai/mcp/_client.py python/tests/test_mcp_openai.py
git commit -m "feat(mcp): add OpenAI function calling adapter"
```

---

## Task 7: Create LangChain Adapter

**Files:**
- Create: `python/src/metadata_ai/mcp/_langchain.py`
- Test: `python/tests/test_mcp_langchain.py`

**Step 1: Write failing test for as_langchain_tools**

Create `python/tests/test_mcp_langchain.py`:

```python
"""Tests for MCP LangChain adapter."""

import json

import pytest
from pytest_httpx import HTTPXMock

pytest.importorskip("langchain_core")

from metadata_ai.client import MetadataAI
from metadata_ai.mcp._models import MCPTool


@pytest.fixture
def client():
    """MetadataAI client fixture."""
    c = MetadataAI(
        host="https://metadata.example.com",
        token="test-token",
        max_retries=0,
    )
    yield c
    c.close()


@pytest.fixture
def mock_list_tools(httpx_mock: HTTPXMock):
    """Mock list_tools response."""
    httpx_mock.add_response(
        url="https://metadata.example.com/mcp",
        method="POST",
        json={
            "jsonrpc": "2.0",
            "id": "test",
            "result": {
                "tools": [
                    {
                        "name": "search_metadata",
                        "description": "Search for metadata",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string", "description": "Search query"},
                            },
                            "required": ["query"],
                        },
                    },
                ]
            },
        },
    )


class TestAsLangChainTools:
    """Tests for MCPClient.as_langchain_tools()."""

    def test_returns_langchain_base_tools(self, client, mock_list_tools):
        """as_langchain_tools returns list of BaseTool instances."""
        from langchain_core.tools import BaseTool

        tools = client.mcp.as_langchain_tools()

        assert len(tools) == 1
        assert isinstance(tools[0], BaseTool)
        assert tools[0].name == "search_metadata"
        assert "Search for metadata" in tools[0].description

    def test_tool_invocation_calls_mcp(self, client, httpx_mock: HTTPXMock):
        """LangChain tool invocation calls MCP server."""
        # Mock list_tools
        httpx_mock.add_response(
            url="https://metadata.example.com/mcp",
            method="POST",
            json={
                "jsonrpc": "2.0",
                "id": "test",
                "result": {
                    "tools": [
                        {
                            "name": "search_metadata",
                            "description": "Search",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query": {"type": "string", "description": "Query"},
                                },
                                "required": ["query"],
                            },
                        },
                    ]
                },
            },
        )
        # Mock tool call
        httpx_mock.add_response(
            url="https://metadata.example.com/mcp",
            method="POST",
            json={
                "jsonrpc": "2.0",
                "id": "test",
                "result": {
                    "content": [{"type": "text", "text": '{"tables": ["customers"]}'}]
                },
            },
        )

        tools = client.mcp.as_langchain_tools()
        result = tools[0].invoke({"query": "customer"})

        assert "customers" in result

    def test_filters_with_exclude(self, client, httpx_mock: HTTPXMock):
        """as_langchain_tools filters with exclude parameter."""
        httpx_mock.add_response(
            url="https://metadata.example.com/mcp",
            method="POST",
            json={
                "jsonrpc": "2.0",
                "id": "test",
                "result": {
                    "tools": [
                        {"name": "search_metadata", "description": "Search", "inputSchema": {}},
                        {"name": "patch_entity", "description": "Patch", "inputSchema": {}},
                    ]
                },
            },
        )

        tools = client.mcp.as_langchain_tools(exclude=[MCPTool.PATCH_ENTITY])

        assert len(tools) == 1
        assert tools[0].name == "search_metadata"
```

**Step 2: Run test to verify it fails**

```bash
cd python && pytest tests/test_mcp_langchain.py -v
```

Expected: FAIL with "AttributeError: 'MCPClient' object has no attribute 'as_langchain_tools'"

**Step 3: Create LangChain adapter module**

Create `python/src/metadata_ai/mcp/_langchain.py`:

```python
"""LangChain adapter for MCP tools.

Requires: pip install metadata-ai[langchain]
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from metadata_ai.mcp._client import MCPClient

try:
    from langchain_core.callbacks import CallbackManagerForToolRun
    from langchain_core.tools import BaseTool, ToolException
    from pydantic import BaseModel, Field, create_model
except ImportError as e:
    raise ImportError(
        "LangChain integration requires langchain-core. "
        "Install with: pip install metadata-ai[langchain]"
    ) from e

from metadata_ai.mcp._models import MCPTool, ToolInfo


def build_langchain_tools(
    mcp_client: MCPClient,
    tools: list[ToolInfo],
) -> list[BaseTool]:
    """
    Convert ToolInfo list to LangChain BaseTool instances.

    Args:
        mcp_client: MCPClient for executing tool calls
        tools: List of ToolInfo from MCP server

    Returns:
        List of LangChain BaseTool instances
    """
    return [_create_langchain_tool(mcp_client, info) for info in tools]


def _create_langchain_tool(mcp_client: MCPClient, info: ToolInfo) -> BaseTool:
    """Create a LangChain tool that calls the MCP server."""
    args_schema = _build_args_schema(info)

    # Create tool class dynamically
    class MCPToolWrapper(BaseTool):
        name: str = info.name.value
        description: str = info.description
        args_schema: type[BaseModel] = args_schema

        _mcp_client: MCPClient
        _tool_name: MCPTool

        def __init__(self, mcp_client: MCPClient, tool_name: MCPTool, **kwargs: Any):
            super().__init__(**kwargs)
            self._mcp_client = mcp_client
            self._tool_name = tool_name

        def _run(
            self,
            run_manager: CallbackManagerForToolRun | None = None,
            **kwargs: Any,
        ) -> str:
            result = self._mcp_client.call_tool(self._tool_name, kwargs)
            if not result.success:
                raise ToolException(result.error or "Tool execution failed")
            return json.dumps(result.data)

    return MCPToolWrapper(mcp_client=mcp_client, tool_name=info.name)


def _build_args_schema(info: ToolInfo) -> type[BaseModel]:
    """Dynamically create Pydantic model from tool parameters."""
    fields: dict[str, Any] = {}

    for param in info.parameters:
        python_type = _mcp_type_to_python(param.type)
        if param.required:
            fields[param.name] = (python_type, Field(description=param.description))
        else:
            fields[param.name] = (
                python_type | None,
                Field(default=None, description=param.description),
            )

    if not fields:
        # Empty schema - add a placeholder
        fields["__placeholder__"] = (str | None, Field(default=None, description=""))

    return create_model(f"{info.name.value}_args", **fields)


def _mcp_type_to_python(mcp_type: str) -> type:
    """Convert MCP type string to Python type."""
    type_map = {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
        "array": list,
        "object": dict,
    }
    return type_map.get(mcp_type, str)
```

**Step 4: Add as_langchain_tools method to MCPClient**

Add to `python/src/metadata_ai/mcp/_client.py` in MCPClient class:

```python
    def as_langchain_tools(
        self,
        include: list[MCPTool] | None = None,
        exclude: list[MCPTool] | None = None,
    ) -> list:
        """
        Get tools formatted for LangChain.

        Requires: pip install metadata-ai[langchain]

        Args:
            include: Only include these tools (allowlist)
            exclude: Exclude these tools (blocklist)

        Returns:
            List of LangChain BaseTool instances
        """
        from metadata_ai.mcp._langchain import build_langchain_tools

        tools = self.list_tools()
        filtered = _filter_tools(tools, include, exclude)
        return build_langchain_tools(self, filtered)
```

**Step 5: Run test to verify it passes**

```bash
cd python && pytest tests/test_mcp_langchain.py -v
```

Expected: PASS

**Step 6: Commit**

```bash
git add python/src/metadata_ai/mcp/_langchain.py python/src/metadata_ai/mcp/_client.py python/tests/test_mcp_langchain.py
git commit -m "feat(mcp): add LangChain adapter for MCP tools"
```

---

## Task 8: Run Full Test Suite and Lint

**Step 1: Run all tests**

```bash
cd python && pytest -v
```

Expected: All PASS

**Step 2: Run linter**

```bash
make lint
```

Expected: PASS

**Step 3: Fix any lint issues**

If there are issues, fix them following the linter suggestions.

**Step 4: Commit any fixes**

```bash
git add -A && git commit -m "fix: address lint issues in MCP implementation"
```

---

## Task 9: Update Package Exports (Optional)

**Files:**
- Modify: `python/src/metadata_ai/__init__.py` (if needed for public API)

**Note:** Per dignified-python standards, we don't re-export. Users import from canonical location:

```python
from metadata_ai.mcp._models import MCPTool
```

If the team decides to make `MCPTool` part of the public API:

```python
from metadata_ai.mcp import MCPTool  # Would require updating mcp/__init__.py
```

This is a team decision - skip if not needed.

---

## Summary

After completing all tasks:

1. **New files created:**
   - `python/src/metadata_ai/mcp/__init__.py`
   - `python/src/metadata_ai/mcp/_models.py`
   - `python/src/metadata_ai/mcp/_client.py`
   - `python/src/metadata_ai/mcp/_openai.py`
   - `python/src/metadata_ai/mcp/_langchain.py`
   - `python/tests/test_mcp_models.py`
   - `python/tests/test_mcp_client.py`
   - `python/tests/test_mcp_openai.py`
   - `python/tests/test_mcp_langchain.py`

2. **Modified files:**
   - `python/src/metadata_ai/exceptions.py` (added MCP exceptions)
   - `python/src/metadata_ai/client.py` (added `mcp` property)

3. **Usage:**
   ```python
   from metadata_ai import MetadataAI
   from metadata_ai.mcp._models import MCPTool

   client = MetadataAI(host="...", token="...")

   # List tools
   tools = client.mcp.list_tools()

   # LangChain
   langchain_tools = client.mcp.as_langchain_tools(
       exclude=[MCPTool.PATCH_ENTITY]
   )

   # OpenAI
   openai_tools = client.mcp.as_openai_tools()
   executor = client.mcp.create_tool_executor()
   ```
