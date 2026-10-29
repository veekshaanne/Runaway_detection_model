"""
CircuitBreaker — autonomous safeguard for the Runaway Agent Monitoring System.

States:
  CLOSED    — Normal operation; requests flow through.
  OPEN      — Tripped by excessive failures; all requests are rejected.
  HALF_OPEN — Recovery probe; one request is allowed to test the system.

Integration:
  The TelemetryMiddleware calls record_failure() / record_success() based on
  the Controller's decision (block/pause → failure; allow/throttle → success).
  When the breaker trips to OPEN, all subsequent requests are short-circuited
  before reaching the ActionGateway.
"""
import threading
import time
from enum import Enum


class CBState(str, Enum):
    CLOSED    = "CLOSED"
    OPEN      = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreaker:
    """
    Thread-safe circuit breaker.

    Integrates with TelemetryMiddleware to autonomously stop, pause, or
    throttle the agent when repeated runaway detections are observed.

    Args:
        failure_threshold: Consecutive failures before opening (default: 3).
        recovery_timeout:  Seconds to wait in OPEN before entering HALF_OPEN (default: 30).
        half_open_max:     Successes in HALF_OPEN needed before closing (default: 1).

    State transitions:
        CLOSED  --[failures >= threshold]--> OPEN
        OPEN    --[recovery_timeout elapsed]--> HALF_OPEN
        HALF_OPEN --[success]--> CLOSED
        HALF_OPEN --[failure]--> OPEN
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout: float = 30.0,
        half_open_max: int = 1,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout  = recovery_timeout
        self.half_open_max     = half_open_max

        self._state         = CBState.CLOSED
        self._failure_count  = 0
        self._success_count  = 0
        self._opened_at: float | None = None
        self._lock          = threading.Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def state(self) -> str:
        """Current state as a plain string: 'CLOSED', 'OPEN', or 'HALF_OPEN'."""
        return self._state.value

    @property
    def failure_count(self) -> int:
        """Number of consecutive failures recorded since the last reset."""
        return self._failure_count

    def allow_request(self) -> bool:
        """Return True if the next request should be allowed through."""
        with self._lock:
            if self._state == CBState.CLOSED:
                return True

            if self._state == CBState.OPEN:
                if self._should_attempt_reset():
                    self._transition(CBState.HALF_OPEN)
                    return True
                return False

            # HALF_OPEN: allow one probe request
            return True

    def record_success(self) -> None:
        """Notify the breaker that the last action succeeded."""
        with self._lock:
            if self._state == CBState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.half_open_max:
                    self._reset()
            elif self._state == CBState.CLOSED:
                # Reset rolling failure count on success
                self._failure_count = 0

    def record_failure(self) -> None:
        """Notify the breaker that the last action failed (blocked/paused)."""
        with self._lock:
            self._failure_count += 1
            if self._failure_count >= self.failure_threshold:
                self._transition(CBState.OPEN)

    def force_reset(self) -> None:
        """Manually reset the breaker to CLOSED (e.g., from a dashboard)."""
        with self._lock:
            self._reset()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _should_attempt_reset(self) -> bool:
        if self._opened_at is None:
            return False
        return time.monotonic() - self._opened_at >= self.recovery_timeout

    def _transition(self, new_state: CBState) -> None:
        self._state = new_state
        if new_state == CBState.OPEN:
            self._opened_at     = time.monotonic()
            self._success_count = 0
        elif new_state == CBState.HALF_OPEN:
            self._success_count = 0

    def _reset(self) -> None:
        self._state         = CBState.CLOSED
        self._failure_count  = 0
        self._success_count  = 0
        self._opened_at      = None

    def __repr__(self) -> str:
        return (
            f"CircuitBreaker(state={self._state.value}, "
            f"failures={self._failure_count}/{self.failure_threshold})"
        )
