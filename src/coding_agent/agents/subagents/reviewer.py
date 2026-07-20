from __future__ import annotations

from coding_agent.agents.results import SubagentRunResult
from coding_agent.agents.subagents.base import BaseSubagent
from coding_agent.agents.subagents.context import SubagentRunContext


class ReviewerSubagent(BaseSubagent):
    spec_name = "reviewer"

    def recommendation_options(self) -> str:
        return "approved|changes_requested|blocked"

    def after_run(
        self,
        context: SubagentRunContext,
        result: SubagentRunResult,
    ) -> None:
        if result.recommendation == "approved":
            context.state.add_observation("reviewer decision: approved")
            return

        if result.recommendation == "changes_requested":
            context.state.mark_changes_requested(
                f"reviewer decision: changes_requested. {result.summary}"
            )
            return

        if result.recommendation == "blocked":
            context.state.mark_blocked(
                f"reviewer decision: blocked. {result.summary}"
            )
