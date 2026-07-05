from __future__ import annotations

from coding_agent.core.task_state import TaskState


class ExecutionMemory:
    """Short-lived execution memory for the current process."""

    def __init__(self):
        self.completed_tasks: list[TaskState] = []

    def record(self, task_state: TaskState) -> None:
        self.completed_tasks.append(task_state)

    def latest_summary(self) -> str:
        if not self.completed_tasks:
            return "No completed tasks in this process."

        latest = self.completed_tasks[-1]
        return (
            f"Latest task: {latest.original_request}\n"
            f"Status: {latest.status}\n"
            f"Iterations: {latest.iterations}\n"
            f"Files modified: {', '.join(latest.files_modified) or 'none'}"
        )
