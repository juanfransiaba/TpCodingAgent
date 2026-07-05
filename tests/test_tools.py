import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from coding_agent.tools.code_search_tool import CodeSearchTool
from coding_agent.tools.file_tool import FileTool


class CommandToolTests(unittest.TestCase):
    def test_file_and_code_search_tools(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "sample.py"

            file_tool = FileTool()
            write_result = file_tool.execute(
                {
                    "action": "write",
                    "path": str(file_path),
                    "content": "def hello():\n    return 'world'\n",
                }
            )
            read_result = file_tool.execute(
                {
                    "action": "read",
                    "path": str(file_path),
                }
            )

            search_tool = CodeSearchTool()
            search_result = search_tool.execute(
                {
                    "action": "search",
                    "query": "hello",
                    "directory": temp_dir,
                }
            )

            self.assertIn("File written successfully", write_result)
            self.assertIn("return 'world'", read_result)
            self.assertIn("sample.py:1", search_result)


if __name__ == "__main__":
    unittest.main()
