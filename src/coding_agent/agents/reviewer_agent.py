from __future__ import annotations

from coding_agent.core.contracts import AgentContext, AgentState
from coding_agent.core.task_state import AgentResult
from coding_agent.prompts.reviewer_prompt import REVIEWER_PROMPT


class ReviewerAgent:
    """Specialized agent that reviews risk and evidence before final output."""

    name = "reviewer"

    def run(self, state: AgentState, _context: AgentContext) -> AgentResult:
        summary_lines = [
            "ReviewerAgent summary:",
            f"- Agent results recorded: {len(state.agent_results)}",
            f"- Files marked modified: {len(state.files_modified)}",
            f"- Tool calls recorded: {len(state.tool_calls)}",
            f"- Errors recorded: {len(state.errors)}",
            "- Review checklist:",
            "  - Does the answer satisfy the original request?",
            "  - Are repository claims backed by tool evidence?",
            "  - Were risky commands and writes checked by permissions?",
            "  - Were tests or validation commands actually run before claiming success?",
        ]

        if state.errors:
            summary_lines.append("- Known errors:")
            summary_lines.extend(f"  - {error}" for error in state.errors[-5:])

        summary_lines.extend(
            [
                "- Role instruction:",
                REVIEWER_PROMPT.strip(),
            ]
        )

        return AgentResult(agent_name=self.name, summary="\n".join(summary_lines))
