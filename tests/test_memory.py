import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from coding_agent.core.task_state import TaskState
from coding_agent.memory.project_memory import ProjectMemory


class ProjectMemoryTests(unittest.TestCase):
    def test_persists_decisions_and_episodes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            memory_path = Path(temp_dir) / "project_memory.json"
            memory = ProjectMemory(memory_path)

            memory.remember_decision(
                topic="architecture",
                decision="Use an agent pipeline",
                rationale="It keeps responsibilities separated.",
            )

            task_state = TaskState(original_request="run local tests")
            task_state.mark_completed("Tests completed.")
            memory.record_task_state(task_state)

            reloaded = ProjectMemory(memory_path)
            context = reloaded.get_relevant_context()

            self.assertIn("Use an agent pipeline", context)
            self.assertIn("run local tests", context)
            self.assertIn("Tests completed.", context)


if __name__ == "__main__":
    unittest.main()
