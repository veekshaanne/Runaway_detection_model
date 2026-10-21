
import argparse

from agent.simulated_agent import SimulatedAgent
from event_logger import EventLogger
from gateway.action_gateway import ActionGateway
from mock_tools import MockTools


def run_frequency_scenario(gateway):
    queries = [
        "weather forecast",
        "database indexing",
        "python file handling",
        "network security",
        "image classification",
        "cloud storage",
        "graph traversal",
    ]

    for i, query in enumerate(queries, 1):
        action = {
            "task_id": "frequency-demo",
            "action_id": i,
            "action_type": "search",
            "target": "web",
            "arguments": {"query": query},
        }

        result = gateway.submit(action)
        print(
            f"Action {i}: search -> {result['decision']} "
            f"(risk={result['risk_score']:.2f})"
        )

        if result["reasons"]:
            print("Reasons: " + ", ".join(result["reasons"]))


def run_semantic_scenario(gateway):
    queries = [
        "how to install python on ubuntu",
        "how to install python in ubuntu",
    ]

    for i, query in enumerate(queries, 1):
        action = {
            "task_id": "semantic-demo",
            "action_id": i,
            "action_type": "search",
            "target": "web",
            "arguments": {"query": query},
        }

        result = gateway.submit(action)
        print(
            f"Action {i}: search -> {result['decision']} "
            f"(risk={result['risk_score']:.2f})"
        )

        if result["reasons"]:
            print("Reasons: " + ", ".join(result["reasons"]))


def run_progress_scenario(gateway):
    tools = gateway.tools

    for path in ["a.txt", "b.txt", "c.txt"]:
        tools.files[path] = "Sample content"

    paths = ["a.txt", "b.txt", "c.txt", "notes.txt"]

    for i, path in enumerate(paths, 1):
        action = {
            "task_id": "progress-demo",
            "action_id": i,
            "action_type": "read_file",
            "target": path,
            "arguments": {"path": path},
        }

        result = gateway.submit(action)
        print(
            f"Action {i}: read_file -> {result['decision']} "
            f"(risk={result['risk_score']:.2f})"
        )

        if result["reasons"]:
            print("Reasons: " + ", ".join(result["reasons"]))


def main():
    parser = argparse.ArgumentParser(
        description="Runaway Agent Monitoring"
    )
    parser.add_argument(
        "--scenario",
        choices=[
            "normal",
            "repetitive",
            "cyclic",
            "frequency",
            "semantic",
            "progress",
        ],
        default="normal",
    )
    parser.add_argument("--db", default="monitor.db")
    args = parser.parse_args()

    tools = MockTools()
    logger = EventLogger(args.db)
    gateway = ActionGateway(
        tools,
        logger,
        repeat_limit=3,
    )

    if args.scenario == "frequency":
        run_frequency_scenario(gateway)
    elif args.scenario == "semantic":
        run_semantic_scenario(gateway)
    elif args.scenario == "progress":
        run_progress_scenario(gateway)
    else:
        agent = SimulatedAgent(gateway, args.scenario)
        agent.run()

    print("Events saved to " + args.db)


if __name__ == "__main__":
    main()
