from __future__ import annotations

from coding_agent.core.contracts import AgentContext, AgentState
from coding_agent.core.task_state import AgentResult
from coding_agent.prompts.coder_prompt import CODER_PROMPT

WRITE_INTENT_KEYWORDS = (
    "agrega",
    "agregar",
    "arregla",
    "arreglar",
    "cambia",
    "cambiar",
    "crea",
    "crear",
    "edita",
    "editar",
    "implementa",
    "implementar",
    "mejora",
    "mejorar",
    "refactor",
)


class CoderAgent:

    name = "coder"

    def run(self, state: AgentState, context: AgentContext) -> AgentResult:
        request = state.original_request.lower()
        write_intent = any(keyword in request for keyword in WRITE_INTENT_KEYWORDS)

        summary_lines = [
            "CoderAgent summary:",
            f"- Write intent detected: {write_intent}",
            "- Implementation strategy:",
            "  - Inspect relevant files before any write.",
            "  - Keep edits scoped to the requested responsibility.",
            "  - Prefer existing helpers, config, and tool interfaces.",
            "  - Record modified files through TaskState/tool tracking.",
        ]

        if not write_intent:
            summary_lines.append(
                "- Current request may be analysis-only; edit only if explicitly needed."
            )

        summary_lines.extend(
            [
                "- Role instruction:",
                CODER_PROMPT.strip(),
            ]
        )

        return AgentResult(agent_name=self.name, summary="\n".join(summary_lines))
