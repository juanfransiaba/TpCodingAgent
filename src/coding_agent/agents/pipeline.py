from __future__ import annotations

from collections.abc import Iterable

from coding_agent.agents.coder_agent import CoderAgent
from coding_agent.agents.planner_agent import PlannerAgent
from coding_agent.agents.reviewer_agent import ReviewerAgent
from coding_agent.agents.test_agent import TestAgent
from coding_agent.core.contracts import Agent, AgentContext, AgentState
from coding_agent.core.task_state import AgentResult


class AgentPipeline:
    """Runs specialized agents in a simple plan -> code -> test -> review flow."""

    def __init__(self, agents: Iterable[Agent]):
        self.agents = list(agents)

    def run(self, state: AgentState, context: AgentContext) -> list[str]:
        summaries: list[str] = []

        for agent in self.agents:
            state.add_progress(f"{agent.name} agent started.")

            try:
                result = agent.run(state, context)
            except Exception as error:
                result = AgentResult(
                    agent_name=getattr(agent, "name", agent.__class__.__name__),
                    summary=f"Agent failed: {error}",
                    status="error",
                )
                state.add_error(result.summary)

            state.add_agent_result(
                result.agent_name,
                result.summary,
                status=result.status,
            )
            summaries.append(result.summary)
            state.add_progress(f"{result.agent_name} agent finished.")

        return summaries


def default_pipeline() -> AgentPipeline:
    return AgentPipeline(
        [
            PlannerAgent(),
            CoderAgent(),
            TestAgent(),
            ReviewerAgent(),
        ]
    )
