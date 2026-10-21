
import os
import tempfile
import unittest

from event_logger import EventLogger
from gateway.action_gateway import ActionGateway
from mock_tools import MockTools


class GatewayTests(unittest.TestCase):
    def setUp(self):
        handle, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        self.tools = MockTools()
        self.logger = EventLogger(self.db_path)
        self.gateway = ActionGateway(
            self.tools, self.logger,
            repeat_limit=2,
            frequency_limit=5,
            window_seconds=10,
        )

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def make_action(self, action_type, target="web", arguments=None):
        return {
            "task_id": "test",
            "action_id": 1,
            "action_type": action_type,
            "target": target,
            "arguments": arguments or {},
        }

    def test_repeated_action_is_blocked_before_tool_execution(self):
        action = self.make_action(
            "search", arguments={"query": "same"}
        )

        first = self.gateway.submit(action)
        second = self.gateway.submit(action)
        third = self.gateway.submit(action)

        self.assertEqual(first["decision"], "allow")
        self.assertEqual(second["decision"], "allow")
        self.assertEqual(third["decision"], "block")
        self.assertEqual(self.tools.searches, 2)

    def test_normal_actions_are_allowed(self):
        action = self.make_action(
            "read_file", "notes.txt", {"path": "notes.txt"}
        )

        result = self.gateway.submit(action)

        self.assertEqual(result["decision"], "allow")
        self.assertTrue(result["result"]["ok"])

    def test_cycle_is_blocked(self):
        actions = [
            self.make_action(
                "read_file", "notes.txt", {"path": "notes.txt"}
            ),
            self.make_action(
                "undo_file", "notes.txt", {"path": "notes.txt"}
            ),
            self.make_action(
                "read_file", "notes.txt", {"path": "notes.txt"}
            ),
            self.make_action(
                "undo_file", "notes.txt", {"path": "notes.txt"}
            ),
        ]

        results = [
            self.gateway.submit(action) for action in actions
        ]

        self.assertEqual(results[-1]["decision"], "block")

    def test_frequency_limit_is_enforced(self):
        results = []

        for i in range(6):
            action = self.make_action(
                "search", "web", {"query": "query" + str(i)}
            )
            results.append(self.gateway.submit(action))

        self.assertEqual(results[4]["decision"], "allow")
        self.assertEqual(results[5]["decision"], "pause")

    def test_finish_is_allowed_after_frequency_limit(self):
        for i in range(6):
            action = self.make_action(
                "search", "web", {"query": "query" + str(i)}
            )
            self.gateway.submit(action)

        finish = self.make_action("finish", "task")
        result = self.gateway.submit(finish)

        self.assertEqual(result["decision"], "allow")

    def test_semantically_similar_action_is_blocked(self):
        first = self.make_action(
            "search", "web",
            {"query": "how to install python on ubuntu"}
        )
        second = self.make_action(
            "search", "web",
            {"query": "how to install python in ubuntu"}
        )

        result1 = self.gateway.submit(first)
        result2 = self.gateway.submit(second)

        self.assertEqual(result1["decision"], "allow")
        self.assertNotEqual(result2["decision"], "allow")
        self.assertIn(
            "semantically similar actions", result2["reasons"]
        )
        self.assertEqual(self.tools.searches, 1)

    def test_meaningful_progress_resets_counter(self):
        self.gateway.progress_monitor.no_progress_count = 2

        result = self.tools.execute({
            "action_type": "complete_file",
            "target": "notes.txt",
            "arguments": {
                "path": "notes.txt",
                "content": "A new note",
            },
        })

        assessment = self.gateway.progress_monitor.check(result)

        self.assertTrue(result["progress"])
        self.assertEqual(assessment["no_progress_count"], 0)
        self.assertFalse(assessment["suspicious"])

    def test_repeated_searches_count_as_no_progress(self):
        action = {
            "action_type": "search",
            "target": "web",
            "arguments": {"query": "same query"},
        }

        self.tools.execute(action)

        for _ in range(3):
            result = self.tools.execute(action)
            assessment = self.gateway.progress_monitor.check(result)

        self.assertFalse(result["progress"])
        self.assertTrue(assessment["suspicious"])
        self.assertEqual(assessment["no_progress_count"], 3)

    def test_gateway_throttles_after_no_progress(self):
        self.tools.files["a.txt"] = "Content A"
        self.tools.files["b.txt"] = "Content B"
        self.tools.files["c.txt"] = "Content C"

        actions = [
            self.make_action(
                "read_file", path, {"path": path}
            )
            for path in ["a.txt", "b.txt", "c.txt"]
        ]

        results = [
            self.gateway.submit(action) for action in actions
        ]

        self.assertEqual(results[0]["decision"], "allow")
        self.assertEqual(results[1]["decision"], "allow")
        self.assertEqual(results[2]["decision"], "allow")
        self.assertEqual(
            self.gateway.progress_monitor.no_progress_count, 3
        )

        next_action = self.make_action(
            "read_file", "notes.txt", {"path": "notes.txt"}
        )
        result = self.gateway.submit(next_action)

        self.assertEqual(result["decision"], "throttle")
        self.assertIn("lack of progress", result["reasons"])


if __name__ == "__main__":
    unittest.main()
