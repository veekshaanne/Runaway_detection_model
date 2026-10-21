from typing import Any, Dict, Optional


def make_event(task_id, action_id, action_type, target, arguments,
               timestamp, result, risk_score, decision):
    return {
        "task_id": task_id,
        "action_id": action_id,
        "action_type": action_type,
        "target": target,
        "arguments": arguments,
        "timestamp": timestamp,
        "result": result,
        "risk_score": risk_score,
        "decision": decision,
    }
