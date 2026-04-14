import os
import tempfile
import unittest

from vooc.services.session_memory import SessionMemory


class SessionMemoryTests(unittest.TestCase):
    def test_session_context_persistence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "sessions.json")
            memory = SessionMemory(store_path=path, context_window=3)
            memory.create_session("s1")
            memory.append("s1", "user", "hello")
            memory.append("s1", "assistant", "hi")

            reloaded = SessionMemory(store_path=path, context_window=3)
            context = reloaded.build_context_text("s1")
            self.assertIn("user: hello", context)
            self.assertIn("assistant: hi", context)


if __name__ == "__main__":
    unittest.main()
