import time
import unittest

from circuit_breaker import CBState, CircuitBreaker


class TestCircuitBreaker(unittest.TestCase):

    def test_starts_closed(self):
        cb = CircuitBreaker()
        self.assertEqual(cb.state, "CLOSED")
        self.assertTrue(cb.allow_request())

    def test_opens_after_threshold_failures(self):
        cb = CircuitBreaker(failure_threshold=2)
        cb.record_failure()
        self.assertEqual(cb.state, "CLOSED")
        cb.record_failure()
        self.assertEqual(cb.state, "OPEN")
        self.assertFalse(cb.allow_request())

    def test_resets_failure_count_on_success_in_closed(self):
        """A success in CLOSED state resets the rolling failure count."""
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        # After reset, two more failures should not open the breaker
        cb.record_failure()
        cb.record_failure()
        self.assertEqual(cb.state, "CLOSED")

    def test_transitions_to_half_open_after_timeout(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.01)
        cb.record_failure()
        self.assertEqual(cb.state, "OPEN")
        time.sleep(0.05)
        self.assertTrue(cb.allow_request())  # triggers HALF_OPEN transition
        self.assertEqual(cb.state, "HALF_OPEN")

    def test_closes_after_success_in_half_open(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.01,
                            half_open_max=1)
        cb.record_failure()
        time.sleep(0.05)
        cb.allow_request()      # → HALF_OPEN
        cb.record_success()
        self.assertEqual(cb.state, "CLOSED")
        self.assertTrue(cb.allow_request())

    def test_reopens_on_failure_in_half_open(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.01)
        cb.record_failure()
        time.sleep(0.05)
        cb.allow_request()      # → HALF_OPEN
        cb.record_failure()
        self.assertEqual(cb.state, "OPEN")

    def test_force_reset(self):
        cb = CircuitBreaker(failure_threshold=1)
        cb.record_failure()
        self.assertEqual(cb.state, "OPEN")
        cb.force_reset()
        self.assertEqual(cb.state, "CLOSED")
        self.assertTrue(cb.allow_request())

    def test_repr_contains_state(self):
        cb = CircuitBreaker(failure_threshold=3)
        self.assertIn("CLOSED", repr(cb))
        self.assertIn("0/3", repr(cb))

    def test_open_state_blocks_until_timeout(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=60.0)
        cb.record_failure()
        self.assertFalse(cb.allow_request())
        self.assertFalse(cb.allow_request())


if __name__ == "__main__":
    unittest.main()
