from coding_agent.core.task_state import TaskState
from coding_agent.prompts.reviewer_prompt import REVIEWER_PROMPT


def run(task_state: TaskState, config: dict) -> str:
    """Produce a review-oriented risk summary from the current task state."""

    summary_lines = [
        "Reviewer summary:",
        f"- Files already marked modified: {len(task_state.files_modified)}",
        f"- Errors recorded: {len(task_state.errors)}",
        f"- Tool calls recorded: {len(task_state.tool_calls)}",
    ]

    if task_state.files_modified:
        summary_lines.append("- Modified files:")
        summary_lines.extend(f"  - {path}" for path in task_state.files_modified)

    if task_state.errors:
        summary_lines.append("- Known errors:")
        summary_lines.extend(f"  - {error}" for error in task_state.errors[-5:])

    summary_lines.extend(
        [
            "- Review checklist:",
            "  - Confirm changes answer the original request.",
            "  - Confirm security policies were respected.",
            "  - Confirm claims are backed by repo evidence, tool output, RAG, memory, or web sources.",
            "  - Confirm tests or validation commands were actually run before claiming success.",
            "- Role instruction:",
            REVIEWER_PROMPT.strip(),
        ]
    )

    summary = "\n".join(summary_lines)
    task_state.add_agent_result("reviewer", summary)
    return summary
