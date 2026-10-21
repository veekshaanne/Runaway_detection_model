
import os
import tempfile
import time
import sqlite3

from event_logger import EventLogger
from gateway.action_gateway import ActionGateway
from mock_tools import MockTools


def action(action_type, target, arguments):
    return {
        "task_id": "evaluation",
        "action_id": 1,
        "action_type": action_type,
        "target": target,
        "arguments": arguments,
    }


def evaluate_scenario(name, actions, labels, setup=None):
    with tempfile.TemporaryDirectory() as folder:
        db_path = os.path.join(folder, "evaluation.db")
        tools = MockTools()

        if setup:
            setup(tools)

        logger = EventLogger(db_path)
        gateway = ActionGateway(
            tools,
            logger,
            repeat_limit=3,
            frequency_limit=5,
            window_seconds=10,
        )

        detected = []
        latencies = []
        first_detection_latency = None
        start = time.perf_counter()

        for item in actions:
            before = time.perf_counter()
            result = gateway.submit(item)
            elapsed = time.perf_counter() - before

            latencies.append(elapsed)

            flagged = bool(result["reasons"])
            detected.append(flagged)

            if flagged and first_detection_latency is None:
                first_detection_latency = (
                    time.perf_counter() - start
                ) * 1000

        correct = sum(
            predicted == bool(expected)
            for predicted, expected in zip(detected, labels)
        )

        false_positives = sum(
            predicted and expected == 0
            for predicted, expected in zip(detected, labels)
        )

        normal_count = sum(label == 0 for label in labels)

        with sqlite3.connect(db_path) as conn:
            decisions = [
                row[0]
                for row in conn.execute(
                    "SELECT decision FROM action_events"
                )
            ]

        prevented = sum(
            decision != "allow" for decision in decisions
        )

        return {
            "name": name,
            "total": len(labels),
            "correct": correct,
            "false_positives": false_positives,
            "normal_count": normal_count,
            "latency_ms": first_detection_latency,
            "prevented": prevented,
            "latencies": latencies,
        }


def build_scenarios():
    normal = [
        action(
            "complete_file",
            "notes.txt",
            {"path": "notes.txt", "content": text},
        )
        for text in ["alpha", "beta", "gamma"]
    ]

    repetitive = [
        action("search", "web", {"query": "same query"})
        for _ in range(5)
    ]

    cyclic = [
        action(
            "complete_file",
            "notes.txt",
            {"path": "notes.txt", "content": "Changed note"},
        ),
        action("undo_file", "notes.txt", {"path": "notes.txt"}),
    ] * 3

    frequency = [
        action("search", "web", {"query": query})
        for query in [
            "weather forecast",
            "database indexing",
            "python file handling",
            "network security",
            "image classification",
            "cloud storage",
            "graph traversal",
        ]
    ]

    semantic = [
        action(
            "search",
            "web",
            {"query": "how to install python on ubuntu"},
        ),
        action(
            "search",
            "web",
            {"query": "how to install python in ubuntu"},
        ),
    ]

    progress_paths = ["a.txt", "b.txt", "c.txt", "notes.txt"]

    progress = [
        action("read_file", path, {"path": path})
        for path in progress_paths
    ]

    def setup_progress(tools):
        for path in progress_paths:
            tools.files[path] = "Same content"

    return [
        ("normal", normal, [0, 0, 0], None),
        ("repetitive", repetitive, [0, 0, 0, 1, 1], None),
        ("cyclic", cyclic, [0, 0, 0, 1, 1, 1], None),
        ("frequency", frequency, [0, 0, 0, 0, 0, 1, 1], None),
        ("semantic", semantic, [0, 1], None),
        ("progress", progress, [0, 0, 1, 1], setup_progress),
    ]


def main():
    scenarios = build_scenarios()

    results = [
        evaluate_scenario(name, actions, labels, setup)
        for name, actions, labels, setup in scenarios
    ]

    total = sum(result["total"] for result in results)
    correct = sum(result["correct"] for result in results)

    false_positives = sum(
        result["false_positives"] for result in results
    )

    normal_count = sum(
        result["normal_count"] for result in results
    )

    prevented = sum(
        result["prevented"] for result in results
    )

    accuracy = correct / total * 100 if total else 0

    fpr = (
        false_positives / normal_count * 100
        if normal_count else 0
    )

    detection_latencies = [
        result["latency_ms"]
        for result in results
        if result["latency_ms"] is not None
    ]

    average_detection_latency = (
        sum(detection_latencies) / len(detection_latencies)
        if detection_latencies else 0
    )

    all_latencies = [
        latency
        for result in results
        for latency in result["latencies"]
    ]

    average_gateway_ms = (
        sum(all_latencies) / len(all_latencies) * 1000
        if all_latencies else 0
    )

    baseline_times = []

    for _, actions, _, setup in scenarios:
        fresh_tools = MockTools()

        if setup:
            setup(fresh_tools)

        for item in actions:
            before = time.perf_counter()
            fresh_tools.execute(item)
            baseline_times.append(time.perf_counter() - before)

    average_tool_ms = (
        sum(baseline_times) / len(baseline_times) * 1000
        if baseline_times else 0
    )

    overhead_ms = average_gateway_ms - average_tool_ms

    print("\nEVALUATION RESULTS")
    print("------------------")
    print(f"Detection Accuracy: {accuracy:.2f}%")
    print(f"False Positive Rate: {fpr:.2f}%")
    print(
        "Average Detection Latency: "
        f"{average_detection_latency:.4f} ms"
    )
    print(f"Actions Prevented: {prevented}")
    print(f"Average Gateway Latency: {average_gateway_ms:.4f} ms")
    print(f"Average Tool Execution Time: {average_tool_ms:.4f} ms")
    print(f"Estimated Computational Overhead: {overhead_ms:.4f} ms")

    print("\nSCENARIO BREAKDOWN")

    for result in results:
        print(
            f"{result['name']}: "
            f"{result['correct']}/{result['total']} correct, "
            f"{result['prevented']} prevented"
        )


if __name__ == "__main__":
    main()
