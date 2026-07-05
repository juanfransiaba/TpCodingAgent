from __future__ import annotations

from typing import Any

from coding_agent.tools.command_base import CommandTool
from coding_agent.tools.repo_tools import search_code, tree_files, view_file


class CodeSearchTool(CommandTool):
    """Command-style wrapper for repository search and inspection."""

    name = "code_search_tool"
    description = "Searches and inspects repository files."
    schema = {
        "type": "object",
        "properties": {
            "action": {"type": "string"},
            "query": {"type": "string"},
            "directory": {"type": "string"},
            "path": {"type": "string"},
            "max_depth": {"type": "integer"},
            "start_line": {"type": "integer"},
            "end_line": {"type": "integer"},
        },
        "required": ["action"],
    }

    def execute(self, arguments: dict[str, Any]) -> str:
        action = arguments.get("action")

        if action == "tree":
            return tree_files(
                str(arguments.get("directory", ".")),
                int(arguments.get("max_depth", 4)),
            )

        if action == "search":
            return search_code(
                str(arguments.get("query", "")),
                str(arguments.get("directory", ".")),
            )

        if action == "view":
            return view_file(
                str(arguments.get("path", "")),
                arguments.get("start_line"),
                arguments.get("end_line"),
            )

        return f"Error: unsupported code search action: {action}"
