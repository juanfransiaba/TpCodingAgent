from __future__ import annotations

from dataclasses import dataclass

from coding_agent.prompts.system_prompt import SYSTEM_PROMPT


@dataclass(frozen=True)
class OrchestratorSettings:
    """Runtime settings for the interactive orchestrator."""

    memory_path: str = "memory/project_memory.json"
    task_states_path: str = "runs/task_states"
    system_prompt: str = SYSTEM_PROMPT
    plan_command: str = "/plan"
    supervision_command: str = "/supervision"
    exit_command: str = "/exit"
    raise_on_error: bool = False
    max_iterations: int = 8

    @classmethod
    def from_config(cls, config: dict) -> "OrchestratorSettings":
        orchestrator_config = config.get("orchestrator", {})

        return cls(
            memory_path=config.get("memory", {}).get(
                "path",
                cls.memory_path,
            ),
            task_states_path=config.get("runs", {}).get(
                "task_states_path",
                cls.task_states_path,
            ),
            plan_command=orchestrator_config.get("plan_command", cls.plan_command),
            supervision_command=orchestrator_config.get(
                "supervision_command",
                cls.supervision_command,
            ),
            exit_command=orchestrator_config.get("exit_command", cls.exit_command),
            raise_on_error=orchestrator_config.get(
                "raise_on_error",
                cls.raise_on_error,
            ),
            max_iterations=orchestrator_config.get(
                "max_iterations",
                cls.max_iterations,
            ),
        )
