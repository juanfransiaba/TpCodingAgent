from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from coding_agent.tools.command_base import CommandTool


class GitTool(CommandTool):
    """Small Git adapter for read-only repository inspection."""

    name = "git_tool"
    description = "Runs safe Git inspection commands."
    schema = {
        "type": "object",
        "properties": {
            "action": {"type": "string"},
            "directory": {"type": "string"},
        },
        "required": ["action"],
    }

    def execute(self, arguments: dict[str, Any]) -> str:
        action = str(arguments.get("action", "status"))
        directory = Path(str(arguments.get("directory", "."))).resolve()

        commands = {
            "status": ["git", "status", "--short"],
            "diff": ["git", "diff", "--"],
        }

        command = commands.get(action)

        if not command:
            return f"Error: unsupported git action: {action}"

        try:
            result = subprocess.run(
                command,
                cwd=directory,
                capture_output=True,
                text=True,
                timeout=30,
                shell=False,
            )
        except Exception as error:
            return f"Error running git {action}: {error}"

        output = ""

        if result.stdout:
            output += f"STDOUT:\n{result.stdout}\n"

        if result.stderr:
            output += f"STDERR:\n{result.stderr}\n"

        output += f"Return code: {result.returncode}"
        return output
