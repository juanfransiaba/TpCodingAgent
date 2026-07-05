from __future__ import annotations

from typing import Any


class CommandTool:
    """Base class for tools implemented with the Command pattern."""

    name = ""
    description = ""
    schema: dict[str, Any] = {}

    def execute(self, arguments: dict[str, Any]) -> str:
        raise NotImplementedError
