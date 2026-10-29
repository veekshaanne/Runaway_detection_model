"""
TelemetryMiddleware wraps ActionGateway.submit() with OpenTelemetry spans.

Tracks per-action:
  - Latency (ms)
  - Simulated token count (proportional to argument text length)
  - Risk score and decision
  - Runaway detection reasons (recorded as OTel span events)
  - Circuit-breaker state transitions (recorded as span events)
"""
import time

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

# Semantic-convention attribute names (GenAI / custom)
_ATTR_ACTION_TYPE   = "agent.action.type"
_ATTR_ACTION_TARGET = "agent.action.target"
_ATTR_RISK_SCORE    = "agent.risk_score"
_ATTR_DECISION      = "agent.decision"
_ATTR_TOKEN_COUNT   = "llm.token.count"
_ATTR_LATENCY_MS    = "agent.latency_ms"
_ATTR_CB_STATE      = "circuit_breaker.state"
_ATTR_TASK_ID       = "agent.task_id"


def _estimate_tokens(action: dict) -> int:
    """
    Heuristic token estimate: 1 token ≈ 4 characters of argument text.
    Replace with a real tokenizer when a live LLM is wired in.
    """
    text = str(action.get("arguments", ""))
    return max(1, len(text) // 4)


class TelemetryMiddleware:
    """
    Wraps an ActionGateway with OpenTelemetry instrumentation.

    Each call to submit() opens an OTel span that records latency, token
    estimates, risk scores, decisions, and any runaway-detection events.
    Circuit-breaker state is checked before forwarding to the gateway and
    updated after based on the Controller's decision.

    Usage:
        middleware = TelemetryMiddleware(gateway, tracer)
        result = middleware.submit(action)
    """

    def __init__(self, gateway, tracer, circuit_breaker=None):
        self.gateway = gateway
        self.tracer = tracer
        self.circuit_breaker = circuit_breaker
        self._total_tokens = 0
        self._action_count = 0

    @property
    def total_tokens(self) -> int:
        """Cumulative estimated token count across all submitted actions."""
        return self._total_tokens

    @property
    def action_count(self) -> int:
        """Number of actions submitted through this middleware."""
        return self._action_count

    def submit(self, action: dict) -> dict:
        """Instrument a single action through the gateway."""
        action_type = action.get("action_type", "unknown")
        task_id     = action.get("task_id", "unknown")

        with self.tracer.start_as_current_span(
            f"action.{action_type}",
            kind=trace.SpanKind.INTERNAL,
        ) as span:
            span.set_attributes(
                {
                    _ATTR_ACTION_TYPE:   action_type,
                    _ATTR_ACTION_TARGET: action.get("target", ""),
                    _ATTR_TASK_ID:       task_id,
                }
            )

            # --- Circuit-breaker pre-check ---
            if self.circuit_breaker is not None:
                cb_state = self.circuit_breaker.state
                span.set_attribute(_ATTR_CB_STATE, cb_state)
                if not self.circuit_breaker.allow_request():
                    span.add_event(
                        "circuit_breaker.rejected",
                        {"circuit_breaker.state": cb_state},
                    )
                    span.set_status(
                        Status(StatusCode.ERROR, "Circuit breaker OPEN")
                    )
                    return {
                        "decision": "block",
                        "risk_score": 1.0,
                        "result": {
                            "ok": False,
                            "progress": False,
                            "message": (
                                f"Circuit breaker is {cb_state}. Request rejected."
                            ),
                        },
                        "reasons": ["circuit breaker open"],
                    }

            # --- Measure gateway latency ---
            t_start = time.perf_counter()
            result = self.gateway.submit(action)
            latency_ms = (time.perf_counter() - t_start) * 1000

            # --- Token estimation ---
            tokens = _estimate_tokens(action)
            self._total_tokens += tokens
            self._action_count += 1

            # --- Attach telemetry attributes ---
            span.set_attributes(
                {
                    _ATTR_RISK_SCORE:  result["risk_score"],
                    _ATTR_DECISION:    result["decision"],
                    _ATTR_TOKEN_COUNT: tokens,
                    _ATTR_LATENCY_MS:  round(latency_ms, 3),
                }
            )

            # --- Record runaway events as OTel span events ---
            for reason in result.get("reasons", []):
                span.add_event(
                    "runaway.detected",
                    {
                        "reason": reason,
                        "risk_score": result["risk_score"],
                        "decision": result["decision"],
                    },
                )

            # --- Circuit-breaker feedback ---
            if self.circuit_breaker is not None:
                if result["decision"] in ("block", "pause"):
                    self.circuit_breaker.record_failure()
                    span.add_event(
                        "circuit_breaker.failure_recorded",
                        {
                            "failures": self.circuit_breaker.failure_count,
                            "threshold": self.circuit_breaker.failure_threshold,
                        },
                    )
                else:
                    self.circuit_breaker.record_success()

            # --- Mark span error if action was blocked ---
            if result["decision"] == "block":
                span.set_status(
                    Status(StatusCode.ERROR, "Action blocked by gateway")
                )
            else:
                span.set_status(Status(StatusCode.OK))

            return result
