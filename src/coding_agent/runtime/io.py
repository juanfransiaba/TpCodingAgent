from __future__ import annotations

from typing import Protocol


class UserIO(Protocol):
    """Input/output boundary used by interactive orchestration."""

    def write(self, message: str = "") -> None:
        """Write a message to the user."""

    def ask(self, prompt: str) -> str:
        """Ask the user for input."""


class ConsoleIO:
    """Console adapter for the default CLI experience."""

    def write(self, message: str = "") -> None:
        print(message)

    def ask(self, prompt: str) -> str:
        return input(prompt)
