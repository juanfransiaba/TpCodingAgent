from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from coding_agent.core.task_state import AgentResult, TaskState

AgentState = TaskState


@dataclass
class AgentContext:
    config: dict[str, Any]
    memory: Any | None = None
    retriever: Any | None = None
    llm: Any | None = None


class Agent(Protocol):
    name: str

    def run(self, state: AgentState, context: AgentContext) -> AgentResult:
        """Run one agent step and return an agent result."""


class Tool(Protocol):
    name: str
    description: str
    schema: dict[str, Any]

    def execute(self, arguments: dict[str, Any]) -> str:
        """Execute the tool command."""


class LLMClient(Protocol):
    model: str

    def chat(self, messages: list[dict], **kwargs) -> Any:
        """Send chat messages to the model."""

    def plan(self, messages: list[dict], task: str) -> str:
        """Generate a plan without executing tools."""


class MemoryStore(Protocol):
    def get_relevant_context(self) -> str:
        """Return compact memory context."""

    def record_task_state(self, task_state: AgentState) -> None:
        """Persist important task state after a milestone."""


class Retriever(Protocol):
    def search(self, query: str, top_k: int = 3) -> str:
        """Retrieve relevant context for a query."""


class Orchestrator(Protocol):
    def handle_command(self, user_input: str) -> str | None:
        """Handle an interactive command when the input is not a task."""

    def run_turn(self, user_input: str) -> None:
        """Run one user task."""
