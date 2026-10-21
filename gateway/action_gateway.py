
from monitor.repetition_detector import RepetitionDetector
from monitor.cycle_detector import CycleDetector
from monitor.frequency_detector import FrequencyDetector
from monitor.progress_monitor import ProgressMonitor
from monitor.semantic_detector import SemanticDetector
from risk_engine import RiskEngine
from controller import Controller


class ActionGateway:
    def __init__(self, tools, logger, repeat_limit=3,
                 frequency_limit=5, window_seconds=10):
        self.tools = tools
        self.logger = logger
        self.repetition_detector = RepetitionDetector(repeat_limit)
        self.cycle_detector = CycleDetector()
        self.semantic_detector = SemanticDetector()
        self.frequency_detector = FrequencyDetector(
            frequency_limit, window_seconds
        )
        self.progress_monitor = ProgressMonitor()
        self.risk_engine = RiskEngine()
        self.controller = Controller()

    def submit(self, action):
        repetition = self.repetition_detector.check(action)
        cycle = self.cycle_detector.check(action)
        semantic = self.semantic_detector.check(action)

        is_finish = action.get("action_type") == "finish"

        if is_finish:
            frequency = {
                "suspicious": False,
                "action_count": 0,
                "risk_score": 0.0,
            }
        else:
            frequency = self.frequency_detector.check()

        no_progress = (
            self.progress_monitor.no_progress_count
            >= self.progress_monitor.no_progress_limit
        )

        progress = {
            "suspicious": no_progress,
            "risk_score": 0.5 if no_progress else 0.0,
        }

        assessment = self.risk_engine.calculate(
            repetition, cycle, frequency, progress, semantic
        )

        decision = self.controller.decide(
            assessment["risk_score"], assessment["reasons"]
        )

        if decision == "allow":
            result = self.tools.execute(action)

            if not is_finish:
                progress = self.progress_monitor.check(result)

                if progress["suspicious"]:
                    assessment["reasons"].append("lack of progress")
                    assessment["risk_score"] = max(
                        assessment["risk_score"],
                        progress["risk_score"],
                    )
        else:
            result = {
                "ok": False,
                "progress": False,
                "message": "Action rejected: " + decision,
            }

        self.logger.log(
            action, result, assessment["risk_score"], decision, assessment["reasons"]
        )

        return {
            "decision": decision,
            "risk_score": assessment["risk_score"],
            "result": result,
            "reasons": assessment["reasons"],
        }
