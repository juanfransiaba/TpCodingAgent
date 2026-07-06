from __future__ import annotations

from coding_agent.core.contracts import AgentContext, AgentState
from coding_agent.core.task_state import AgentResult
from coding_agent.prompts.planner_prompt import PLANNER_PROMPT

IMPLEMENTATION_KEYWORDS = (
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

VALIDATION_KEYWORDS = (
    "evaluar",
    "test",
    "tests",
    "probar",
    "validar",
    "verificar",
)

DOCUMENTATION_KEYWORDS = (
    "documenta",
    "documentar",
    "docs",
    "informe",
    "readme",
    "resumen",
)


class PlannerAgent:
    """Specialized agent that turns the user request into an execution plan."""

    name = "planner"

    def run(self, state: AgentState, context: AgentContext) -> AgentResult:
        workspace = context.config.get("workspace", ".")
        task_type = classify_task(state.original_request)
        steps = planning_steps(task_type)

        summary_lines = [
            "PlannerAgent summary:",
            f"- Workspace: {workspace}",
            f"- Task type: {task_type}",
            (
                "- Context already collected: "
                f"{len(state.sources)} source(s), "
                f"{len(state.agent_results)} previous agent result(s)."
            ),
            "- Recommended focus:",
        ]
        summary_lines.extend(f"  {index}. {step}" for index, step in enumerate(steps, 1))
        summary_lines.extend(
            [
                "- Role instruction:",
                PLANNER_PROMPT.strip(),
            ]
        )

        return AgentResult(agent_name=self.name, summary="\n".join(summary_lines))


def classify_task(request: str) -> str:
    normalized = request.lower()

    if any(keyword in normalized for keyword in VALIDATION_KEYWORDS):
        return "validation"

    if any(keyword in normalized for keyword in DOCUMENTATION_KEYWORDS):
        return "documentation"

    if any(keyword in normalized for keyword in IMPLEMENTATION_KEYWORDS):
        return "implementation"

    return "analysis"


def planning_steps(task_type: str) -> list[str]:
    if task_type == "implementation":
        return [
            "Use Explorer/Researcher output as initial context, then inspect only the files directly related to the change.",
            "Make the smallest scoped edit that answers the request.",
            "Run focused validation before claiming the change works.",
            "Review modified files, tool evidence, and errors before final response.",
        ]

    if task_type == "validation":
        return [
            "Identify the most relevant validation command for the workspace.",
            "Run the command through the controlled terminal tool.",
            "Summarize pass/fail evidence and avoid claiming success without command output.",
        ]

    if task_type == "documentation":
        return [
            "Inspect the current documentation before editing or summarizing.",
            "Use recorded sources, memory, and RAG context to avoid unsupported claims.",
            "Keep documentation changes focused on the requested section.",
        ]

    return [
        "Use collected context and inspect files only when evidence is missing.",
        "Answer without writing files unless the user explicitly asks for changes.",
        "Mention uncertainty or missing evidence instead of guessing.",
    ]
