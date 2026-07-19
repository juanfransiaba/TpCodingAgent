from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from coding_agent.core.task_state import TaskState

AgentState = TaskState


@dataclass
class AgentContext:
    config: dict[str, Any]
    memory: Any | None = None
    llm: Any | None = None


class MemoryStore(Protocol):
    def get_relevant_context(self) -> str:
        """Return compact memory context."""

    def record_task_state(self, task_state: AgentState) -> None:
        """Persist important task state after a milestone."""
