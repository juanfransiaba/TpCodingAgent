import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from coding_agent.core.task_state import TaskState


class TaskStateTests(unittest.TestCase):
    def test_tracks_write_file_as_modified_file(self):
        task_state = TaskState(original_request="crear archivo")

        task_state.add_tool_call(
            tool_name="write_file",
            args={"path": "src/example.py"},
            allowed=True,
            result="ok",
            iteration=1,
        )
        task_state.add_tool_call(
            tool_name="write_file",
            args={"path": "src/example.py"},
            allowed=True,
            result="ok again",
            iteration=2,
        )

        self.assertEqual(task_state.files_modified, ["src/example.py"])

    def test_json_roundtrip_keeps_nested_records(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            task_state = TaskState(original_request="buscar docs")
            task_state.add_source(
                kind="rag",
                title="data leakage",
                location="rag_docs/data_leakage.md",
                summary="usar fechas anteriores",
            )
            task_state.add_agent_result("planner", "plan listo")
            task_state.mark_completed("respuesta final")

            path = task_state.save_json(Path(temp_dir) / "task_state.json")
            loaded = TaskState.load_json(path)

            self.assertEqual(loaded.original_request, "buscar docs")
            self.assertEqual(loaded.status, "completed")
            self.assertEqual(loaded.sources[0].title, "data leakage")
            self.assertEqual(loaded.agent_results[0].agent_name, "planner")


if __name__ == "__main__":
    unittest.main()
