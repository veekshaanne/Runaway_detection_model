
class Controller:
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
