
class MockTools:
    def __init__(self):
        self.files = {"notes.txt": "Initial note"}
        self.searches = 0
        self.seen_queries = set()

    def execute(self, action):
        name = action.get("action_type")
        args = action.get("arguments", {})

        if name == "read_file":
            path = args.get("path", "")
            if path not in self.files:
                return {
                    "ok": False,
                    "progress": False,
                    "message": "File not found",
                }
            return {
                "ok": True,
                "progress": False,
                "content": self.files[path],
            }

        if name == "complete_file":
            path = args.get("path", "")
            content = args.get("content", "")
            changed = self.files.get(path) != content
            self.files[path] = content
            return {
                "ok": True,
                "progress": changed,
                "message": "File updated",
            }

        if name == "undo_file":
            path = args.get("path", "")
            changed = self.files.get(path) != "Initial note"
            self.files[path] = "Initial note"
            return {
                "ok": True,
                "progress": changed,
                "message": "File restored",
            }

        if name == "search":
            self.searches += 1
            query = args.get("query", "")
            progress = query not in self.seen_queries
            self.seen_queries.add(query)
            return {
                "ok": True,
                "progress": progress,
                "message": "Mock search completed",
                "search_count": self.searches,
            }

        if name == "finish":
            return {
                "ok": True,
                "progress": False,
                "message": "Task finished",
            }

        return {
            "ok": False,
            "progress": False,
            "message": "Unknown tool",
        }
