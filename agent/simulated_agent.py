class SimulatedAgent:
    def __init__(self, gateway, scenario):
        self.gateway = gateway
        self.scenario = scenario

    def run(self):
        actions = self._get_actions()
        for index, action in enumerate(actions, start=1):
            action["task_id"] = self.scenario
            action["action_id"] = index
            response = self.gateway.submit(action)
            print("Action {0}: {1} -> {2} (risk={3:.2f})".format(
                index, action["action_type"], response["decision"],
                response["risk_score"]))
            if action["action_type"] == "finish" and response["decision"] == "allow":
                print("Task completed.")
                return
        print("Scenario ended.")

    def _get_actions(self):
        if self.scenario == "normal":
            return [
                {"action_type": "read_file", "target": "notes.txt",
                 "arguments": {"path": "notes.txt"}},
                {"action_type": "complete_file", "target": "notes.txt",
                 "arguments": {"path": "notes.txt", "content": "Updated note"}},
                {"action_type": "finish", "target": "task", "arguments": {}},
            ]
        if self.scenario == "repetitive":
            return [
                {"action_type": "search", "target": "web",
                 "arguments": {"query": "same query"}}
                for _ in range(7)
            ] + [{"action_type": "finish", "target": "task", "arguments": {}}]
        if self.scenario == "cyclic":
            return [
                {"action_type": "read_file", "target": "notes.txt",
                 "arguments": {"path": "notes.txt"}},
                {"action_type": "undo_file", "target": "notes.txt",
                 "arguments": {"path": "notes.txt"}},
                {"action_type": "read_file", "target": "notes.txt",
                 "arguments": {"path": "notes.txt"}},
                {"action_type": "undo_file", "target": "notes.txt",
                 "arguments": {"path": "notes.txt"}},
                {"action_type": "read_file", "target": "notes.txt",
                 "arguments": {"path": "notes.txt"}},
                {"action_type": "undo_file", "target": "notes.txt",
                 "arguments": {"path": "notes.txt"}},
            ]
        raise ValueError("Unknown scenario: " + self.scenario)
