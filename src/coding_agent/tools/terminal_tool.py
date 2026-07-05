from __future__ import annotations

from typing import Any

from coding_agent.tools.command_base import CommandTool
from coding_agent.tools.command_tool import run_command


class TerminalTool(CommandTool):
    """Command-style wrapper for terminal execution."""

    name = "terminal_tool"
    description = "Runs terminal commands."
    schema = {
        "type": "object",
        "properties": {
            "command": {"type": "string"},
        },
        "required": ["command"],
    }

    def execute(self, arguments: dict[str, Any]) -> str:
        return run_command(str(arguments.get("command", "")))
