from __future__ import annotations

from typing import Any

from coding_agent.tools.command_base import CommandTool
from coding_agent.tools.command_tool import run_command


class TestRunnerTool(CommandTool):
    """Command-style wrapper for project validation commands."""

    name = "test_runner_tool"
    description = "Runs a validation or test command."
    schema = {
        "type": "object",
        "properties": {
            "command": {"type": "string"},
        },
    }

    def execute(self, arguments: dict[str, Any]) -> str:
        command = str(arguments.get("command") or "python -m compileall src")
        return run_command(command)
