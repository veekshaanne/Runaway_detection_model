
class Controller:
    """
    Decides the action to take given a risk score and detected reasons.

    Decisions:
      block    — Action is rejected outright (highest risk).
      pause    — Agent should pause and await human review.
      throttle — Agent may continue but with a configurable delay.
      allow    — No issues detected; action is permitted.
    """

    # Delay in seconds applied when the decision is 'throttle'
    throttle_seconds: float = 1.0

    def decide(self, risk_score, reasons=None):
        reasons = reasons or []

        if "repeated actions" in reasons or "cyclic behavior" in reasons:
            return "block"
        elif risk_score >= 0.8:
            return "block"
        elif risk_score >= 0.6:
            return "pause"
        elif risk_score >= 0.4:
            return "throttle"
        else:
            return "allow"

    def get_delay(self, decision: str) -> float:
        """Return the number of seconds the agent should sleep for this decision."""
        return self.throttle_seconds if decision == "throttle" else 0.0
