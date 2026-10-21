
class ProgressMonitor:
    def __init__(self, no_progress_limit=3):
        self.no_progress_limit = no_progress_limit
        self.no_progress_count = 0

    def check(self, result):
        meaningful_progress = result.get("progress", False)

        if meaningful_progress:
            self.no_progress_count = 0
        else:
            self.no_progress_count += 1

        suspicious = self.no_progress_count >= self.no_progress_limit

        return {
            "suspicious": suspicious,
            "no_progress_count": self.no_progress_count,
            "risk_score": 0.5 if suspicious else 0.0,
        }
