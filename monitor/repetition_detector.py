
import json


class RepetitionDetector:
    def __init__(self, repeat_limit=3):
        self.repeat_limit = repeat_limit
        self.action_counts = {}

    def _signature(self, action):
        return (
            action.get("action_type", ""),
            action.get("target", ""),
            json.dumps(action.get("arguments", {}), sort_keys=True),
        )

    def check(self, action):
        signature = self._signature(action)
        count = self.action_counts.get(signature, 0) + 1
        self.action_counts[signature] = count

        return {
            "count": count,
            "suspicious": count > self.repeat_limit,
            "risk_score": min(1.0, 0.5 + 0.1 * (count - self.repeat_limit))
            if count > self.repeat_limit else 0.0,
        }
