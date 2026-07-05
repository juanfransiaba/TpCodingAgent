from __future__ import annotations

from typing import Any

from coding_agent.tools.command_base import CommandTool
from coding_agent.tools.file_tools import list_files, read_file, write_file
from coding_agent.tools.repo_tools import view_file


class FileTool(CommandTool):
    """Command-style wrapper for file operations."""

    name = "file_tool"
    description = "Reads, writes, lists, or views files."
    schema = {
        "type": "object",
        "properties": {
            "action": {"type": "string"},
            "path": {"type": "string"},
            "directory": {"type": "string"},
            "content": {"type": "string"},
            "start_line": {"type": "integer"},
            "end_line": {"type": "integer"},
        },
        "required": ["action"],
    }

    def execute(self, arguments: dict[str, Any]) -> str:
        action = arguments.get("action")

        if action == "read":
            return read_file(str(arguments.get("path", "")))

        if action == "write":
            return write_file(
                str(arguments.get("path", "")),
                str(arguments.get("content", "")),
            )

        if action == "list":
            return list_files(str(arguments.get("directory", ".")))

        if action == "view":
            return view_file(
                str(arguments.get("path", "")),
                arguments.get("start_line"),
                arguments.get("end_line"),
            )

        return f"Error: unsupported file action: {action}"
