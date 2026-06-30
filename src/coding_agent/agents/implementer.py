from coding_agent.core.task_state import TaskState
from coding_agent.prompts.implementer_prompt import IMPLEMENTER_PROMPT

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
    "modifica",
    "modificar",
    "refactor",
)


def run(task_state: TaskState, config: dict) -> str:
    """Build an implementation-oriented brief for the main agent."""

    request = task_state.original_request.lower()
    write_intent = any(keyword in request for keyword in WRITE_INTENT_KEYWORDS)

    summary_lines = [
        "Implementer summary:",
        f"- Write intent detected: {write_intent}",
        "- Recommended approach:",
        "  - Inspect relevant files before editing.",
        "  - Apply the smallest change that satisfies the task.",
        "  - Use write_file only for intentional code or document changes.",
        "  - Record modified files in TaskState.",
    ]

    if write_intent:
        summary_lines.append(
            "- The task likely requires code changes; check policies before any write."
        )
    else:
        summary_lines.append(
            "- The task may be analysis-only; avoid edits unless the user clearly asks for them."
        )

    summary_lines.append("- Role instruction:")
    summary_lines.append(IMPLEMENTER_PROMPT.strip())

    summary = "\n".join(summary_lines)
    task_state.add_agent_result("implementer", summary)
    return summary
