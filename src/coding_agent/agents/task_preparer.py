from coding_agent.agents.coordinator import default_coordinator
from coding_agent.core.contracts import AgentContext, MemoryStore
from coding_agent.core.task_state import TaskState
from coding_agent.llm.client import default_llm_client
from coding_agent.runtime.harness import run_agent_turn


def prepare_task(
    task_state: TaskState,
    config: dict,
    memory: MemoryStore | None = None,
    run_agent_turn_fn=run_agent_turn,
    supervision: bool = False,
    trace=None,
) -> str:
    """Run lightweight evidence agents and build the subagent brief."""

    task_state.add_progress("Task preparer started subagent coordination.")

    context = AgentContext(
        config=config,
        memory=memory,
        llm=default_llm_client,
    )
    coordinator = default_coordinator(
        run_agent_turn_fn=run_agent_turn_fn,
        supervision=supervision,
        trace=trace,
        verbose=True,
    )

    subagent_summaries = coordinator.run(task_state, context)

    task_state.add_progress("Task preparer finished subagent coordination.")

    return build_coordination_brief(
        task_state,
        subagent_summaries,
        memory=memory,
    )


def build_coordination_brief(
    task_state: TaskState,
    subagent_summaries: list[str],
    memory: MemoryStore | None = None,
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
            (
                f"- [{source.kind}] {source.title}: {source.location}"
                f"{format_source_detail(source.agent_name, source.query)}"
            )
            for source in task_state.sources
        )

    if (
        task_state.tool_calls
        or task_state.files_modified
        or task_state.observations
        or task_state.errors
    ):
        brief_lines.append("")
        brief_lines.append("Execution evidence:")

        if task_state.files_modified:
            brief_lines.append("- Files modified:")
            brief_lines.extend(f"  - {path}" for path in task_state.files_modified)

        if task_state.tool_calls:
            brief_lines.append("- Tool calls:")
            brief_lines.extend(
                (
                    f"  - {tool_call.tool_name} "
                    f"agent={tool_call.agent_name or 'unknown'} "
                    f"allowed={tool_call.allowed} "
                    f"iteration={tool_call.iteration}"
                )
                for tool_call in task_state.tool_calls[-12:]
            )

        if task_state.observations:
            brief_lines.append("- Observations:")
            brief_lines.extend(
                f"  - {observation}"
                for observation in task_state.observations[-5:]
            )

        if task_state.errors:
            brief_lines.append("- Errors:")
            brief_lines.extend(f"  - {error}" for error in task_state.errors[-5:])

    brief_lines.extend(
        [
            "",
            "Execution instruction:",
            "- Use this brief as shared state, not as a substitute for tool evidence.",
            "- If repository evidence is missing, inspect files with tools before making claims.",
            "- If a command or write is risky, follow policy and approval requirements.",
        ]
    )

    return "\n".join(brief_lines)


def format_source_detail(agent_name: str, query: str) -> str:
    details: list[str] = []

    if agent_name:
        details.append(f"agent={agent_name}")

    if query:
        details.append(f"query={query}")

    if not details:
        return ""

    return f" ({', '.join(details)})"
