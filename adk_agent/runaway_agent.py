"""
RunawayDetectionAgent — google.adk LlmAgent integration.

This module wires the existing Runaway Detection pipeline into an ADK LlmAgent
using before_tool_callback / after_tool_callback lifecycle hooks.

In "mock mode" (no GOOGLE_API_KEY), the agent is run via a headless runner that
exercises the callback/tool path without making live LLM calls — fully usable
in WSL and offline environments.

In production, supply a GOOGLE_API_KEY environment variable and the agent will
use the Gemini model specified by GOOGLE_MODEL (default: gemini-2.5-flash).
"""
import os
import textwrap

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from circuit_breaker import CircuitBreaker
from event_logger import EventLogger
from gateway.action_gateway import ActionGateway
from mock_tools import MockTools
from telemetry.otel_setup import setup_telemetry
from telemetry.telemetry_middleware import TelemetryMiddleware

# --- Configuration -----------------------------------------------------------
MODEL_ID    = os.getenv("GOOGLE_MODEL", "gemini-2.5-flash")
TRACES_FILE = os.getenv("TRACES_FILE", "traces.jsonl")
DB_PATH     = os.getenv("MONITOR_DB", "adk_monitor.db")
APP_NAME    = "runaway_detection_agent"


# =============================================================================
# Tool functions registered with the ADK agent
# =============================================================================

def search_web(query: str) -> dict:
    """Perform a web search. Returns mock search results."""
    return {"ok": True, "message": f"Mock results for: {query}"}


def read_file(path: str) -> dict:
    """Read a file from the mock filesystem."""
    return {"ok": True, "content": f"Mock content of {path}"}


def write_file(path: str, content: str) -> dict:
    """Write content to a file in the mock filesystem."""
    return {"ok": True, "message": f"Wrote {len(content)} chars to {path}"}


# =============================================================================
# Callback factories
# =============================================================================

def make_before_tool_callback(middleware: TelemetryMiddleware):
    """
    Returns a before_tool_callback that submits the pending action to the
    monitoring gateway BEFORE the ADK runtime executes the real tool.

    If the gateway blocks or the circuit breaker is open, the callback
    returns a synthetic response dict, preventing the real tool from running.
    """

    def before_tool_callback(tool, args, tool_context):
        action = {
            "task_id":     tool_context.invocation_id or "adk-task",
            "action_id":   id(args),          # unique per invocation
            "action_type": tool.name,
            "target":      args.get("path", args.get("query", tool.name)),
            "arguments":   args,
        }

        result = middleware.submit(action)
        decision = result["decision"]

        if decision != "allow":
            reasons_str = ", ".join(result.get("reasons", [decision]))
            return {
                "blocked": True,
                "decision": decision,
                "risk_score": result["risk_score"],
                "message": f"Action {decision}ed by monitor [{reasons_str}]",
            }

        # Allow the real ADK tool to execute
        return None

    return before_tool_callback


def make_after_tool_callback(middleware: TelemetryMiddleware):
    """
    Returns an after_tool_callback that can post-process tool output for
    additional telemetry. Extend this hook to capture real output tokens
    or update downstream state.
    """

    def after_tool_callback(tool, args, tool_context, tool_response):
        # No-op hook — extend here to post-process tool output.
        return None

    return after_tool_callback


# =============================================================================
# Agent factory
# =============================================================================

def build_agent(console: bool = True) -> tuple[LlmAgent, TelemetryMiddleware, CircuitBreaker]:
    """
    Construct and return (agent, middleware, circuit_breaker).

    Returns the three objects so callers can inspect telemetry state after a
    run without relying on global state.
    """
    # -- Telemetry setup --
    tracer = setup_telemetry(APP_NAME, traces_file=TRACES_FILE, console=console)

    # -- Monitoring pipeline --
    tools_mock = MockTools()
    logger     = EventLogger(DB_PATH)
    gateway    = ActionGateway(
        tools_mock, logger,
        repeat_limit=3,
        frequency_limit=5,
        window_seconds=10,
    )
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=30.0)
    middleware = TelemetryMiddleware(gateway, tracer, circuit_breaker=cb)

    # -- ADK callbacks --
    before_tool = make_before_tool_callback(middleware)
    after_tool  = make_after_tool_callback(middleware)

    # -- LlmAgent --
    agent = LlmAgent(
        model=MODEL_ID,
        name=APP_NAME,
        description=textwrap.dedent("""\
            An agent that monitors its own tool calls for runaway behaviour such as
            repetitive actions, cyclic loops, and lack of task progress.
        """),
        instruction=textwrap.dedent("""\
            You are a helpful assistant. Use your tools to answer the user's request.
            After each tool call you will receive monitoring feedback.
            If a tool call is blocked, explain why and do not retry the same action.
        """),
        tools=[
            FunctionTool(search_web),
            FunctionTool(read_file),
            FunctionTool(write_file),
        ],
        before_tool_callback=before_tool,
        after_tool_callback=after_tool,
    )

    return agent, middleware, cb


# =============================================================================
# Headless runner (mock mode — no API key required)
# =============================================================================

def run_mock_scenario(scenario: str = "normal") -> None:
    """
    Run a predefined mock scenario through the ADK monitoring stack WITHOUT
    making any live LLM calls.

    The before_tool_callback is invoked directly for each action, exercising
    the full monitoring + telemetry + circuit-breaker pipeline.
    """
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    console = Console()
    console.print(
        Panel(
            f"[bold cyan]ADK Runaway Detection — Scenario: {scenario}[/bold cyan]",
            subtitle="Mock mode · No API key required",
        )
    )

    _, middleware, cb = build_agent()

    # Build action sequences that mirror SimulatedAgent scenarios
    scenarios: dict[str, list[dict]] = {
        "normal": [
            {"action_type": "read_file", "target": "notes.txt",
             "arguments": {"path": "notes.txt"}},
            {"action_type": "complete_file", "target": "notes.txt",
             "arguments": {"path": "notes.txt", "content": "Updated note"}},
            {"action_type": "finish", "target": "task", "arguments": {}},
        ],
        "repetitive": [
            {"action_type": "search", "target": "web",
             "arguments": {"query": "same query"}}
            for _ in range(6)
        ],
        "cyclic": [
            item
            for pair in [
                [
                    {"action_type": "read_file", "target": "notes.txt",
                     "arguments": {"path": "notes.txt"}},
                    {"action_type": "undo_file", "target": "notes.txt",
                     "arguments": {"path": "notes.txt"}},
                ]
            ] * 3
            for item in pair
        ],
    }

    actions = scenarios.get(scenario, scenarios["normal"])

    table = Table(title=f"Scenario: {scenario}", show_lines=True)
    table.add_column("Step",     style="dim",     width=6)
    table.add_column("Action",   style="cyan",    width=18)
    table.add_column("Decision", style="bold",    width=12)
    table.add_column("Risk",     style="yellow",  width=6)
    table.add_column("CB State", style="magenta", width=12)
    table.add_column("Reasons")

    for i, raw_action in enumerate(actions, 1):
        action = {"task_id": f"adk-{scenario}", "action_id": i, **raw_action}
        result = middleware.submit(action)

        decision_colour = {
            "allow":    "green",
            "throttle": "yellow",
            "pause":    "orange3",
            "block":    "red",
        }.get(result["decision"], "white")

        table.add_row(
            str(i),
            action["action_type"],
            f"[{decision_colour}]{result['decision']}[/{decision_colour}]",
            f"{result['risk_score']:.2f}",
            cb.state,
            ", ".join(result.get("reasons", [])) or "—",
        )

    console.print(table)
    console.print(
        f"\n[bold]Estimated tokens:[/bold] {middleware.total_tokens}  "
        f"[bold]Actions:[/bold] {middleware.action_count}  "
        f"[bold]Circuit breaker:[/bold] {cb.state}"
    )
    console.print(f"[dim]OTel traces appended → {TRACES_FILE}[/dim]")
    console.print(f"[dim]Events logged   → {DB_PATH}[/dim]")
