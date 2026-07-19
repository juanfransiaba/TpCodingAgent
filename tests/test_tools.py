import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from coding_agent.tools.file_tools import read_file, write_file
from coding_agent.tools.repo_tools import search_code
from coding_agent.tools.tool_registry import tools_for


class ToolFunctionTests(unittest.TestCase):
    def test_file_and_code_search_functions(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "sample.py"

            write_result = write_file(
                str(file_path),
                "def hello():\n    return 'world'\n",
            )
            read_result = read_file(str(file_path))
            search_result = search_code("hello", temp_dir)

            self.assertIn("File written successfully", write_result)
            self.assertIn("return 'world'", read_result)
            self.assertIn("sample.py:1", search_result)

    def test_tools_for_returns_only_requested_schemas(self):
        tools = tools_for(("read_file", "write_file"))

        self.assertEqual(
            [tool["function"]["name"] for tool in tools],
            ["read_file", "write_file"],
        )


if __name__ == "__main__":
    unittest.main()
