from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class CommandTool(ABC):
    """Base class for tools implemented with the Command pattern."""

    name = ""
    description = ""
    schema: dict[str, Any] = {}

    @abstractmethod
    def execute(self, arguments: dict[str, Any]) -> str:
        raise NotImplementedError
