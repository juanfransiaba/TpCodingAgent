from __future__ import annotations

from coding_agent.core.contracts import AgentState


def count_successful_writes(state: AgentState) -> int:
    return sum(
        1
        for tool_call in state.tool_calls
        if (
            tool_call.tool_name == "write_file"
            and tool_call.allowed
            and tool_call.result_preview.startswith("File written successfully")
        )
    )
