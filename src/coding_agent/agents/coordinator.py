from __future__ import annotations

from collections.abc import Callable
from typing import Any

from coding_agent.agents.router import SubagentRouter, format_route_plan
from coding_agent.agents.subagents import (
    SubagentRegistry,
    SubagentRunContext,
    count_successful_writes,
)
from coding_agent.core.contracts import AgentContext, AgentState
from coding_agent.runtime.harness import run_agent_turn

RunAgentTurnFn = Callable[..., tuple[str, int]]


class SubagentCoordinator:
    """Coordinates routed subagents without owning role-specific behavior."""

    def __init__(
        self,
        router: SubagentRouter | None = None,
        subagent_registry: SubagentRegistry | None = None,
        run_agent_turn_fn: RunAgentTurnFn = run_agent_turn,
        verbose: bool = False,
        supervision: bool = False,
        trace: Any | None = None,
    ):
        self.router = router or SubagentRouter()
        self.subagents = subagent_registry or SubagentRegistry()
        self.run_agent_turn = run_agent_turn_fn
        self.verbose = verbose
        self.supervision = supervision
        self.trace = trace

    def run(self, state: AgentState, context: AgentContext) -> list[str]:
        route_plan = self.router.route(
            state.original_request,
            llm_client=context.llm,
            trace=self.trace,
        )
        selected_names = ", ".join(route_plan.selected_names)
        state.add_progress(f"Subagent router selected: {selected_names}.")
        state.add_observation(format_route_plan(route_plan))

        summaries: list[str] = []
        implementation_attempted = False
        successful_writes_before_implementation = count_successful_writes(state)

        for route_entry in route_plan.selected:
            subagent = self.subagents.get(route_entry.spec.name)
            run_context = SubagentRunContext(
                state=state,
                agent_context=context,
                previous_summaries=summaries,
                run_agent_turn=self.run_agent_turn,
                trace=self.trace,
                supervision=self.supervision,
                verbose=self.verbose,
                route_reason=route_entry.reason,
                implementation_attempted=implementation_attempted,
                successful_writes_before_implementation=(
                    successful_writes_before_implementation
                ),
            )

            if subagent.should_skip(run_context):
                summaries.append(subagent.skip(run_context))
                continue

            state.add_progress(
                f"{subagent.name} subagent started "
                f"({route_entry.reason}) with tools: "
                f"{', '.join(subagent.allowed_tools)}."
            )
            summaries.append(subagent.run(run_context))
            state.add_progress(f"{subagent.name} subagent finished.")

            if subagent.marks_implementation_attempted:
                implementation_attempted = True

        return summaries


def default_coordinator(
    run_agent_turn_fn: RunAgentTurnFn = run_agent_turn,
    verbose: bool = False,
    supervision: bool = False,
    trace: Any | None = None,
) -> SubagentCoordinator:
    return SubagentCoordinator(
        run_agent_turn_fn=run_agent_turn_fn,
        verbose=verbose,
        supervision=supervision,
        trace=trace,
    )
