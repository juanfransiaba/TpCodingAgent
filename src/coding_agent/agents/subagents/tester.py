from __future__ import annotations

from coding_agent.agents.subagents.base import BaseSubagent
from coding_agent.agents.subagents.context import SubagentRunContext
from coding_agent.agents.subagents.write_tracking import count_successful_writes


class TesterSubagent(BaseSubagent):
    spec_name = "tester"

    def should_skip(self, context: SubagentRunContext) -> bool:
        return (
            context.implementation_attempted
            and count_successful_writes(context.state)
            == context.successful_writes_before_implementation
        )

    def skip_reason(self, context: SubagentRunContext) -> str:
        return (
            "tester subagent skipped: implementer finished without "
            "modifying files."
        )
