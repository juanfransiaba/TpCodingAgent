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
                title="nestjs controllers",
                location="rag_docs/nestjs_controllers.md",
                summary="usar decoradores del controller",
                agent_name="researcher",
                query="nestjs controllers",
            )
            task_state.add_agent_result(
                "researcher",
                "docs encontradas",
                evidence=["rag_docs/data_leakage.md"],
                blockers=[],
                recommendation="continue",
            )
            task_state.mark_completed("respuesta final")

            path = task_state.save_json(Path(temp_dir) / "task_state.json")
            loaded = TaskState.load_json(path)

            self.assertEqual(loaded.original_request, "buscar docs")
            self.assertEqual(loaded.status, "completed")
            self.assertEqual(loaded.sources[0].title, "nestjs controllers")
            self.assertEqual(loaded.sources[0].agent_name, "researcher")
            self.assertEqual(loaded.sources[0].query, "nestjs controllers")
            self.assertEqual(loaded.agent_results[0].agent_name, "researcher")
            self.assertEqual(
                loaded.agent_results[0].evidence,
                ["rag_docs/data_leakage.md"],
            )
            self.assertEqual(loaded.agent_results[0].recommendation, "continue")

    def test_records_agent_and_sources_from_source_tools(self):
        task_state = TaskState(original_request="buscar docs")

        task_state.add_tool_call(
            tool_name="search_rag",
            args={"query": "ports and adapters"},
            allowed=True,
            result="Fuente: rag_docs/architecture.md\nContenido:\ntexto",
            iteration=1,
            agent_name="researcher",
        )
        task_state.add_tool_call(
            tool_name="web_search",
            args={"query": "hexagonal architecture"},
            allowed=True,
            result="Results:\n  https://example.com/article\n",
            iteration=2,
            agent_name="researcher",
        )

        self.assertEqual(task_state.tool_calls[0].agent_name, "researcher")
        self.assertEqual(
            [
                (source.kind, source.location, source.agent_name)
                for source in task_state.sources
            ],
            [
                ("rag", "rag_docs/architecture.md", "researcher"),
                ("web", "https://example.com/article", "researcher"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
