
class CycleDetector:
    def __init__(self, max_cycle_size=4):
        self.max_cycle_size = max_cycle_size
        self.history = []

    def check(self, action):
        signature = (
            action.get("action_type", ""),
            action.get("target", ""),
        )
        self.history.append(signature)

        for size in range(2, min(self.max_cycle_size, len(self.history) // 2) + 1):
            first = self.history[-2 * size:-size]
            second = self.history[-size:]

            if first == second and len(set(first)) > 1:
                return {
                    "suspicious": True,
                    "cycle_size": size,
                    "risk_score": 0.7,
                }

        return {
            "suspicious": False,
            "cycle_size": 0,
            "risk_score": 0.0,
        }
