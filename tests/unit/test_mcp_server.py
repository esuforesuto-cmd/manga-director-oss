from __future__ import annotations

import io
import json

from manga_director import __version__
from manga_director.adapters import ImageGeneratorFactory, LLMFactory
from manga_director.agents.registry import primary_agents, support_agents
from manga_director.domain.state_machine import StateMachine
from manga_director.events import MemoryEventBus
from manga_director.mcp import McpServer, build_mcp_server
from manga_director.prompting import PromptPipeline, PromptTemplateLoader
from manga_director.repositories import InMemoryRepository, ProjectLoader
from manga_director.workflow import (
    ChapterWorkflowEngine,
    PageNumberWorkflowScheduler,
    ProjectWorkflowEngine,
    WorkflowCoordinator,
    WorkflowEngine,
)


def _server() -> McpServer:
    repository = InMemoryRepository()
    loader = ProjectLoader(repository)
    events = MemoryEventBus()
    generator = ImageGeneratorFactory.create("mock")
    llm = LLMFactory.create("mock")
    pipeline = PromptPipeline(template_loader=PromptTemplateLoader())
    engine = WorkflowEngine(
        state_machine=StateMachine(),
        event_bus=events,
        agents=primary_agents(generator, None, llm, pipeline),
        support_agents=support_agents(llm, None),
    )
    project_engine = ProjectWorkflowEngine(repository, events)
    coordinator = WorkflowCoordinator(
        project_engine,
        ChapterWorkflowEngine(repository, events, PageNumberWorkflowScheduler()),
        engine,
        loader,
    )
    return build_mcp_server(
        workflow_engine=engine,
        workflow_coordinator=coordinator,
        project_loader=loader,
        repository=repository,
    )


def test_mcp_tool_registry_exposes_validated_tools_and_dtos() -> None:
    server = _server()

    tools = server.tools()
    created = server.call_tool(
        "create_project",
        {"project_id": "demo", "title": "Demo", "metadata": {"genre": "drama"}},
    )
    listed = server.call_tool("list_projects")

    assert any(tool["name"] == "approve_page" for tool in tools)
    assert any(tool["name"] == "planning_summary" for tool in tools)
    assert any(tool["name"] == "provider_selection" for tool in tools)
    assert any(tool["name"] == "workflow_analytics" for tool in tools)
    assert any(tool["name"] == "enterprise_diagnostics" for tool in tools)
    assert any(tool["name"] == "executive_analytics" for tool in tools)
    assert any(tool["name"] == "workflow_reliability" for tool in tools)
    assert any(tool["name"] == "provider_governance" for tool in tools)
    assert any(tool["name"] == "executive_dashboard" for tool in tools)
    assert next(tool for tool in tools if tool["name"] == "create_project")["inputSchema"]
    assert created.success is True
    assert created.operation == "create_project"
    assert listed.success is True
    assert listed.data[0]["metadata"]["genre"] == "drama"


def test_mcp_maps_input_and_transition_errors_without_raising() -> None:
    server = _server()
    server.call_tool("create_project", {"project_id": "demo", "title": "Demo"})

    invalid_input = server.call_tool("design_page", {"project_id": "demo"})
    unexpected_input = server.call_tool("list_projects", {"unexpected": True})
    invalid_transition = server.call_tool("review_page", {"project_id": "demo", "page_number": 1})

    assert invalid_input.success is False
    assert "validation_error" in invalid_input.errors[0]
    assert unexpected_input.success is False
    assert invalid_transition.success is False
    assert "state_transition_error" in invalid_transition.errors[0]


def test_mcp_project_status_exposes_the_read_only_page_readiness_projection() -> None:
    server = _server()
    server.call_tool("create_project", {"project_id": "demo", "title": "Demo"})

    status = server.call_tool("get_project_status", {"project_id": "demo"})

    assert status.success is True
    assert status.data["readiness_summary"] == {
        "completed_page_count": 0,
        "actionable_page_count": 1,
        "blocked_page_count": 0,
        "next_actionable_page_number": 1,
        "first_blocked_page": None,
        "next_actionable_page": status.data["page_readiness"][0],
        "readiness_outcome": "ACTIONABLE",
        "readiness_focus_page": status.data["page_readiness"][0],
    }
    assert status.data["page_readiness"] == [
        {
            "page_number": 1,
            "current_state": "Draft",
            "unmet_prerequisites": [],
            "next_operation": "design",
            "non_execution": True,
        }
    ]


def test_mcp_resources_and_markdown_prompts_are_read_only() -> None:
    server = _server()
    server.call_tool("create_project", {"project_id": "demo", "title": "Demo"})

    resource = server.read_resource("manga://projects/demo/chapters/chapter-1/pages/1")
    prompt = server.get_prompt("design_manga_page", {"project_id": "demo", "page_number": "1"})

    assert resource["mimeType"] == "application/json"
    assert json.loads(resource["text"])["page_number"] == 1
    assert "Project: demo" in prompt
    assert any(item["name"] == "design_manga_page" for item in server.prompts())


def test_mcp_approval_requires_quality_checked_then_uses_workflow_engine() -> None:
    server = _server()
    server.call_tool("create_project", {"project_id": "demo", "title": "Demo"})

    rejected = server.call_tool(
        "approve_page",
        {"project_id": "demo", "page_number": 1, "approved_by": "editor"},
    )
    server.call_tool("run_project", {"project_id": "demo"})
    approved = server.call_tool(
        "approve_page",
        {"project_id": "demo", "page_number": 1, "approved_by": "editor"},
    )

    assert rejected.success is False
    assert approved.success is True
    assert approved.state == "Approved"


def test_mcp_stdio_transport_handles_initialize_and_tools_list() -> None:
    server = _server()
    input_stream = io.StringIO(
        json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
        + "\n"
        + json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        + "\n"
    )
    output_stream = io.StringIO()

    server.serve_stdio(input_stream, output_stream)

    responses = [json.loads(line) for line in output_stream.getvalue().splitlines()]
    assert responses[0]["result"]["capabilities"]["tools"] == {}
    assert responses[0]["result"]["serverInfo"]["version"] == __version__
    assert any(tool["name"] == "create_project" for tool in responses[1]["result"]["tools"])
