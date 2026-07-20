from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from coding_agent.core.contracts import AgentContext, AgentState

RunAgentTurnFn = Callable[..., tuple[str, int]]


@dataclass(frozen=True)
class SubagentRunContext:
    state: AgentState
    agent_context: AgentContext
    previous_summaries: list[str]
    run_agent_turn: RunAgentTurnFn
    trace: Any | None
    supervision: bool
    verbose: bool
    route_reason: str = ""
    implementation_attempted: bool = False
    successful_writes_before_implementation: int = 0
