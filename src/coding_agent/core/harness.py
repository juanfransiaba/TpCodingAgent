import json

from coding_agent.core.llm_client import MODEL, client
from coding_agent.core.permissions import check_permissions
from coding_agent.core.supervision import ask_permission
from coding_agent.tools.tool_registry import (
    TOOL_FUNCTIONS,
    TOOLS,
    TOOLS_WITH_SUPERVISION,
)


def run_agent_turn(
    messages: list[dict],
    config: dict,
    supervision: bool = False,
) -> tuple[str, int]:
    """Runs the inner loop: LLM -> tool calls -> tool results -> LLM."""

    iterations = 0

    while True:
        iterations += 1
        print(f"  [iteration {iterations}] Calling LLM...", end="", flush=True)

        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )

        msg = response.choices[0].message

        assistant_msg = {
            "role": "assistant",
            "content": msg.content or "",
        }

        if msg.tool_calls:
            assistant_msg["tool_calls"] = [
                {
                    "id": tool_call.id,
                    "type": "function",
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments,
                    },
                }
                for tool_call in msg.tool_calls
            ]

        messages.append(assistant_msg)

        if not msg.tool_calls:
            print(" -> final response")
            return msg.content or "", iterations

        print(f" -> wants to use {len(msg.tool_calls)} tool(s)")

        for tool_call in msg.tool_calls:
            tool_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)

            print(f"    🔧 {tool_name}({args})")

            allowed, reason = check_permissions(tool_name, args, config)

            if not allowed:
                result = f"Blocked by policies: {reason}"
                print(f"    🚫 {result}")
                append_tool_result(messages, tool_call.id, result)
                continue

            if supervision and tool_name in TOOLS_WITH_SUPERVISION:
                approved = ask_permission(tool_name, args)

                if not approved:
                    result = f"Action '{tool_name}' rejected by user."
                    print("    ❌ Rejected")
                    append_tool_result(messages, tool_call.id, result)
                    continue

            function = TOOL_FUNCTIONS.get(tool_name)

            if not function:
                result = f"Unknown tool: {tool_name}"
            else:
                result = function(**args)

            append_tool_result(messages, tool_call.id, str(result))


def append_tool_result(messages: list[dict], tool_call_id: str, content: str) -> None:
    messages.append(
        {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": content,
        }
    )
