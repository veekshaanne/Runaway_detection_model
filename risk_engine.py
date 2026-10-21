
class RiskEngine:
    def calculate(self, repetition, cycle, frequency, progress,
                  semantic=None):
        if semantic is None:
            semantic = {
                "suspicious": False,
                "risk_score": 0.0,
            }

        scores = [
            repetition["risk_score"],
            cycle["risk_score"],
            frequency["risk_score"],
            progress["risk_score"],
            semantic["risk_score"],
        ]

        risk_score = max(scores)

        reasons = []

        if repetition["suspicious"]:
            reasons.append("repeated actions")

        if cycle["suspicious"]:
            reasons.append("cyclic behavior")

        if frequency["suspicious"]:
            reasons.append("excessive action frequency")

        if progress["suspicious"]:
            reasons.append("lack of progress")

        if semantic["suspicious"]:
            reasons.append("semantically similar actions")

        return {
            "risk_score": risk_score,
            "suspicious": risk_score > 0,
            "reasons": reasons,
        }
