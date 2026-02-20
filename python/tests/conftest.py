"""Pytest fixtures for AI SDK tests."""

import pytest


# Sample agent info responses
@pytest.fixture
def sample_agent_info_dict():
    """Sample agent info as returned by API."""
    return {
        "name": "DataQualityPlannerAgent",
        "displayName": "Data Quality Planner",
        "description": "Analyzes data quality and suggests improvements",
        "abilities": ["search_metadata", "analyze_quality", "create_tests"],
        "apiEnabled": True,
    }


@pytest.fixture
def sample_invoke_response_dict():
    """Sample invoke response as returned by API."""
    return {
        "conversationId": "550e8400-e29b-41d4-a716-446655440000",
        "response": "The customers table has 3 data quality issues.",
        "toolsUsed": ["search_metadata", "analyze_quality"],
        "usage": {
            "promptTokens": 150,
            "completionTokens": 50,
            "totalTokens": 200,
        },
    }


@pytest.fixture
def sample_agents_list_response(sample_agent_info_dict):
    """Sample list agents response as returned by API."""
    return {
        "data": [
            sample_agent_info_dict,
            {
                "name": "SqlQueryAgent",
                "displayName": "SQL Query Agent",
                "description": "Generates SQL queries",
                "abilities": ["generate_sql", "explain_query"],
                "apiEnabled": True,
            },
        ]
    }


@pytest.fixture
def sample_sse_stream():
    """Sample SSE stream bytes for testing streaming."""
    events = [
        b'event: stream-start\ndata: {"conversationId": "550e8400-e29b-41d4-a716-446655440000"}\n\n',
        b'event: message\ndata: {"content": "The customers "}\n\n',
        b'event: message\ndata: {"content": "table has "}\n\n',
        b'event: tool-use\ndata: {"toolName": "search_metadata"}\n\n',
        b'event: message\ndata: {"content": "3 issues."}\n\n',
        b'event: stream-completed\ndata: {"conversationId": "550e8400-e29b-41d4-a716-446655440000"}\n\n',
    ]
    return events
