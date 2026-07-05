from __future__ import annotations

from coding_agent.core.contracts import AgentContext, AgentState
from coding_agent.core.task_state import AgentResult
from coding_agent.prompts.planner_prompt import PLANNER_PROMPT


class PlannerAgent:
    """Specialized agent that turns the user request into an execution plan."""

    name = "planner"

    def run(self, state: AgentState, context: AgentContext) -> AgentResult:
        workspace = context.config.get("workspace", ".")

        summary = "\n".join(
            [
                "PlannerAgent summary:",
                f"- Workspace: {workspace}",
                "- Proposed pipeline:",
                "  1. Inspect repository structure and relevant files.",
                "  2. Retrieve local documentation or memory when it can reduce uncertainty.",
                "  3. Implement the smallest change that answers the request.",
                "  4. Run focused validation commands.",
                "  5. Review risks, errors, and evidence before the final answer.",
                "- Role instruction:",
                PLANNER_PROMPT.strip(),
            ]
        )

        return AgentResult(agent_name=self.name, summary=summary)
