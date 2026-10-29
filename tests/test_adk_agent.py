import os
import unittest
from types import SimpleNamespace

from adk_agent.runaway_agent import (
    build_agent,
    make_before_tool_callback,
    make_after_tool_callback,
    run_mock_scenario,
    search_web,
    read_file,
    write_file,
)
from circuit_breaker import CircuitBreaker
from event_logger import EventLogger
from gateway.action_gateway import ActionGateway
from mock_tools import MockTools
from opentelemetry.sdk.trace import TracerProvider
from telemetry.telemetry_middleware import TelemetryMiddleware


class TestAdkAgent(unittest.TestCase):

    def setUp(self):
        self.provider = TracerProvider()
        self.tracer = self.provider.get_tracer("test_adk")
        self.db_path = "test_adk_monitor.db"
        self.logger = EventLogger(self.db_path)
        self.tools = MockTools()
        self.gateway = ActionGateway(
            self.tools,
            self.logger,
            repeat_limit=2,
            frequency_limit=5,
            window_seconds=10,
        )
        self.cb = CircuitBreaker(failure_threshold=2, recovery_timeout=30.0)
        self.middleware = TelemetryMiddleware(self.gateway, self.tracer, circuit_breaker=self.cb)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_tools(self):
        res_search = search_web("python test")
        self.assertTrue(res_search["ok"])
        self.assertIn("python test", res_search["message"])

        res_read = read_file("test.txt")
        self.assertTrue(res_read["ok"])
        self.assertIn("test.txt", res_read["content"])

        res_write = write_file("test.txt", "hello world")
        self.assertTrue(res_write["ok"])
        self.assertIn("11 chars", res_write["message"])

    def test_build_agent(self):
        agent, middleware, cb = build_agent()
        self.assertIsNotNone(agent)
        self.assertEqual(agent.name, "runaway_detection_agent")
        self.assertIsNotNone(middleware)
        self.assertIsNotNone(cb)
        self.assertEqual(cb.state, "CLOSED")

    def test_before_tool_callback_allow_and_block(self):
        before_tool = make_before_tool_callback(self.middleware)
        mock_tool = SimpleNamespace(name="search_web")
        mock_context = SimpleNamespace(invocation_id="test_inv_1")

        # 1st call -> allow (returns None)
        res1 = before_tool(mock_tool, {"query": "python"}, mock_context)
        self.assertIsNone(res1)

        # 2nd call -> allow (repeat_limit is 2)
        res2 = before_tool(mock_tool, {"query": "python"}, mock_context)
        self.assertIsNone(res2)

        # 3rd call -> blocked because repeat_limit is exceeded
        res3 = before_tool(mock_tool, {"query": "python"}, mock_context)
        self.assertIsNotNone(res3)
        self.assertTrue(res3.get("blocked"))
        self.assertEqual(res3.get("decision"), "block")

    def test_after_tool_callback(self):
        after_tool = make_after_tool_callback(self.middleware)
        mock_tool = SimpleNamespace(name="search_web")
        mock_context = SimpleNamespace(invocation_id="test_inv_1")
        res = after_tool(mock_tool, {"query": "python"}, mock_context, {"ok": True})
        self.assertIsNone(res)

    def test_mock_scenarios_execute(self):
        for scenario in ["normal", "repetitive", "cyclic"]:
            # Should run without throwing any exceptions
            run_mock_scenario(scenario)
