from __future__ import annotations

from coding_agent.core.task_state import TaskState

RAG_TOOLS = {"rag_search", "search_rag"}


def check_rag_before_web(
    tool_name: str,
    task_state: TaskState | None,
    agent_name: str,
) -> tuple[bool, str]:
    """Require a RAG attempt before a subagent can use web search."""

    if tool_name != "web_search":
        return True, "OK"

    if task_state is None:
        return True, "OK"

    if has_prior_rag_attempt(task_state, agent_name):
        return True, "OK"

    return (
        False,
        (
            "web_search blocked by RAG-first policy: call search_rag before "
            "using web_search, then use web only if local RAG evidence is "
            "missing or insufficient."
        ),
    )


def has_prior_rag_attempt(task_state: TaskState, agent_name: str) -> bool:
    return any(
        tool_call.tool_name in RAG_TOOLS
        and tool_call.allowed
        and tool_call.agent_name == agent_name
        for tool_call in task_state.tool_calls
    )
