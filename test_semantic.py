
from monitor.semantic_detector import SemanticDetector

detector = SemanticDetector()

actions = [
    {
        "action_type": "search",
        "target": "web",
        "arguments": {"query": "how to install python on ubuntu"},
    },
    {
        "action_type": "search",
        "target": "web",
        "arguments": {"query": "how to install python in ubuntu"},
    },
    {
        "action_type": "search",
        "target": "web",
        "arguments": {"query": "best places to visit in japan"},
    },
]

for action in actions:
    print(detector.check(action))
