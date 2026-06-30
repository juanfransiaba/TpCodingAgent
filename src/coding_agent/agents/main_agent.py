from coding_agent.agents import explorer, implementer, researcher, reviewer, tester
from coding_agent.core.task_state import TaskState
from coding_agent.memory.project_memory import ProjectMemory


def prepare_task(
    task_state: TaskState,
    config: dict,
    memory: ProjectMemory | None = None,
) -> str:
    """Run lightweight subagents and build a shared brief for the LLM."""

    task_state.add_progress("Main agent started subagent coordination.")

    subagent_summaries = [
        explorer.run(task_state, config),
        researcher.run(task_state, config, memory=memory),
        implementer.run(task_state, config),
        tester.run(task_state, config),
        reviewer.run(task_state, config),
    ]

    task_state.add_progress("Main agent finished subagent coordination.")

    return build_coordination_brief(
        task_state,
        subagent_summaries,
        memory=memory,
    )


def build_coordination_brief(
    task_state: TaskState,
    subagent_summaries: list[str],
    memory: ProjectMemory | None = None,
) -> str:
    """Convert shared state into a concise message for the model context."""

    brief_lines = [
        "Shared task state and subagent brief.",
        f"Task id: {task_state.task_id}",
        f"Original request: {task_state.original_request}",
        "",
        "Subagent outputs:",
    ]

    if memory:
        brief_lines.append("")
        brief_lines.append(memory.get_relevant_context())

    for summary in subagent_summaries:
        brief_lines.append("")
        brief_lines.append(summary)

    if task_state.sources:
        brief_lines.append("")
        brief_lines.append("Sources recorded:")
        brief_lines.extend(
            f"- [{source.kind}] {source.title}: {source.location}"
            for source in task_state.sources
        )

    brief_lines.extend(
        [
            "",
            "Main agent instruction:",
            "- Use this brief as shared state, not as a substitute for tool evidence.",
            "- If repository evidence is missing, inspect files with tools before making claims.",
            "- If a command or write is risky, follow policy and approval requirements.",
        ]
    )

    return "\n".join(brief_lines)
