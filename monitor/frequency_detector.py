
import time
from collections import deque


class FrequencyDetector:
    def __init__(self, frequency_limit=5, window_seconds=10):
        self.frequency_limit = frequency_limit
        self.window_seconds = window_seconds
        self.action_times = deque()

    def check(self):
        now = time.monotonic()

        while self.action_times and now - self.action_times[0] > self.window_seconds:
            self.action_times.popleft()

        self.action_times.append(now)
        suspicious = len(self.action_times) > self.frequency_limit

        return {
            "suspicious": suspicious,
            "action_count": len(self.action_times),
            "risk_score": 0.6 if suspicious else 0.0,
        }
