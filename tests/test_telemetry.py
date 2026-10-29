import os
import tempfile
import unittest

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)

from circuit_breaker import CircuitBreaker
from event_logger import EventLogger
from gateway.action_gateway import ActionGateway
from mock_tools import MockTools
from telemetry.telemetry_middleware import TelemetryMiddleware


def _make_middleware(exporter: InMemorySpanExporter):
    """Construct a TelemetryMiddleware backed by an in-memory OTel exporter."""
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = provider.get_tracer("test")

    handle, db_path = tempfile.mkstemp(suffix=".db")
    os.close(handle)

    tools   = MockTools()
    logger  = EventLogger(db_path)
    gateway = ActionGateway(tools, logger, repeat_limit=2)
    cb      = CircuitBreaker(failure_threshold=3)
    return TelemetryMiddleware(gateway, tracer, circuit_breaker=cb), db_path


class TestTelemetryMiddleware(unittest.TestCase):

    def setUp(self):
        self.exporter = InMemorySpanExporter()
        self.middleware, self.db_path = _make_middleware(self.exporter)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _action(self, action_type, target="notes.txt", arguments=None):
        return {
            "task_id":     "test",
            "action_id":   1,
            "action_type": action_type,
            "target":      target,
            "arguments":   arguments or {},
        }

    # ------------------------------------------------------------------
    # Span emission
    # ------------------------------------------------------------------

    def test_normal_action_emits_one_span(self):
        self.middleware.submit(
            self._action("read_file", arguments={"path": "notes.txt"})
        )
        spans = self.exporter.get_finished_spans()
        self.assertEqual(len(spans), 1)
        self.assertEqual(spans[0].name, "action.read_file")

    def test_span_has_required_attributes(self):
        self.middleware.submit(
            self._action("read_file", arguments={"path": "notes.txt"})
        )
        attrs = self.exporter.get_finished_spans()[0].attributes
        for key in (
            "agent.risk_score",
            "agent.decision",
            "agent.latency_ms",
            "llm.token.count",
            "agent.task_id",
        ):
            self.assertIn(key, attrs, f"Missing span attribute: {key}")

    # ------------------------------------------------------------------
    # Token / action accounting
    # ------------------------------------------------------------------

    def test_token_count_accumulates(self):
        for _ in range(3):
            self.middleware.submit(
                self._action("search", "web", {"query": "test query"})
            )
        self.assertGreater(self.middleware.total_tokens, 0)
        self.assertEqual(self.middleware.action_count, 3)

    def test_token_estimate_is_positive(self):
        self.middleware.submit(
            self._action("search", "web", {"query": "hello"})
        )
        self.assertGreater(self.middleware.total_tokens, 0)

    # ------------------------------------------------------------------
    # Runaway event recording
    # ------------------------------------------------------------------

    def test_runaway_emits_span_event(self):
        """After repeat_limit exceeded a 'runaway.detected' event should appear."""
        action = self._action("search", "web", {"query": "same"})
        # repeat_limit=2 → first two allowed, third triggers block
        for _ in range(3):
            self.middleware.submit(action)
        all_events = [
            e
            for s in self.exporter.get_finished_spans()
            for e in s.events
            if e.name == "runaway.detected"
        ]
        self.assertTrue(len(all_events) > 0, "Expected runaway.detected event")

    def test_blocked_span_has_error_status(self):
        action = self._action("search", "web", {"query": "same"})
        for _ in range(3):
            self.middleware.submit(action)
        from opentelemetry.trace import StatusCode
        blocked_spans = [
            s for s in self.exporter.get_finished_spans()
            if s.status.status_code == StatusCode.ERROR
        ]
        self.assertTrue(len(blocked_spans) > 0)

    # ------------------------------------------------------------------
    # Circuit-breaker integration
    # ------------------------------------------------------------------

    def test_circuit_breaker_blocks_when_open(self):
        cb = self.middleware.circuit_breaker
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()  # now OPEN
        result = self.middleware.submit(
            self._action("read_file", arguments={"path": "x.txt"})
        )
        self.assertEqual(result["decision"], "block")
        self.assertIn("circuit breaker open", result["reasons"])

    def test_circuit_breaker_rejection_emits_span_event(self):
        cb = self.middleware.circuit_breaker
        for _ in range(3):
            cb.record_failure()
        self.middleware.submit(
            self._action("search", "web", {"query": "x"})
        )
        events = [
            e
            for s in self.exporter.get_finished_spans()
            for e in s.events
            if e.name == "circuit_breaker.rejected"
        ]
        self.assertTrue(len(events) > 0)

    def test_circuit_breaker_records_failure_on_block(self):
        """Middleware should call record_failure when gateway returns block."""
        cb = self.middleware.circuit_breaker
        action = self._action("search", "web", {"query": "same"})
        # 3 identical actions → 3rd is blocked → CB records 1 failure
        for _ in range(3):
            self.middleware.submit(action)
        self.assertGreater(cb.failure_count, 0)


if __name__ == "__main__":
    unittest.main()
