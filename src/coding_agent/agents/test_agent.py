from __future__ import annotations

from pathlib import Path

from coding_agent.agents.tester import suggest_commands
from coding_agent.core.contracts import AgentContext, AgentState
from coding_agent.core.task_state import AgentResult
from coding_agent.prompts.tester_prompt import TESTER_PROMPT


class TestAgent:
    """Specialized agent that proposes validation commands."""

    name = "test"

    def run(self, state: AgentState, context: AgentContext) -> AgentResult:
        workspace = Path(context.config.get("workspace", ".")).resolve()
        commands = suggest_commands(workspace)

        summary_lines = [
            "TestAgent summary:",
            f"- Workspace: {workspace}",
            "- Suggested validation commands:",
        ]

        if commands:
            summary_lines.extend(f"  - {command}" for command in commands)
        else:
            summary_lines.append(
                "  - No project-specific test command detected; use focused syntax/import checks."
            )

        summary_lines.extend(
            [
                "- Role instruction:",
                TESTER_PROMPT.strip(),
            ]
        )

        return AgentResult(agent_name=self.name, summary="\n".join(summary_lines))
