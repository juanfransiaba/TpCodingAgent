from __future__ import annotations

from pathlib import Path

from coding_agent.core.task_state import TaskState
from coding_agent.memory.project_memory import ProjectMemory


class PersistentMemoryStore:
    """Repository-style adapter over ProjectMemory."""

    def __init__(self, storage_path: str | Path):
        self.project_memory = ProjectMemory(storage_path)

    @property
    def storage_path(self) -> Path:
        return self.project_memory.storage_path

    def get_relevant_context(self) -> str:
        return self.project_memory.get_relevant_context()

    def record_task_state(self, task_state: TaskState) -> None:
        self.project_memory.record_task_state(task_state)

    def remember_decision(self, topic: str, decision: str, rationale: str) -> None:
        self.project_memory.remember_decision(topic, decision, rationale)

    def remember_command(self, command: str, purpose: str) -> None:
        self.project_memory.remember_command(command, purpose)
