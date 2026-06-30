import json
import time

from coding_agent.core.llm_client import MODEL, client
from coding_agent.core.permissions import (
    check_permissions,
    normalize_tool_args,
    requires_approval,
)
from coding_agent.core.supervision import ask_permission
from coding_agent.core.task_state import TaskState
from coding_agent.tools.tool_registry import (
    TOOL_FUNCTIONS,
    TOOLS,
    TOOLS_WITH_SUPERVISION,
)


def run_agent_turn(
    messages: list[dict],
    config: dict,
    supervision: bool = False,
    task_state: TaskState | None = None,
    trace=None,
) -> tuple[str, int]:
    """Runs the inner loop: LLM -> tool calls -> tool results -> LLM."""

    iterations = 0

    while True:
        iterations += 1
        if task_state:
            task_state.set_iterations(iterations)
            task_state.add_progress(f"Calling LLM for iteration {iterations}.")

        print(f"  [iteration {iterations}] Calling LLM...", end="", flush=True)

        llm_started_at = time.perf_counter()

        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
            )
        except Exception as error:
            latency_seconds = time.perf_counter() - llm_started_at
            if trace:
                trace.record_llm_call(
                    iteration=iterations,
                    messages=messages,
                    model=MODEL,
                    output="",
                    latency_seconds=latency_seconds,
                    usage=None,
                    error=str(error),
                )
            raise

        llm_latency_seconds = time.perf_counter() - llm_started_at

        msg = response.choices[0].message

        if trace:
            trace.record_llm_call(
                iteration=iterations,
                messages=messages,
                model=MODEL,
                output=msg.content or "",
                latency_seconds=llm_latency_seconds,
                usage=getattr(response, "usage", None),
            )

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
            if task_state:
                task_state.add_agent_result("main_agent", msg.content or "")
            return msg.content or "", iterations

        print(f" -> wants to use {len(msg.tool_calls)} tool(s)")

        for tool_call in msg.tool_calls:
            tool_name = tool_call.function.name

            try:
                args = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError as error:
                result = f"Invalid tool arguments: {error}"
                print(f"    ERROR {tool_name}: {result}")
                if task_state:
                    task_state.add_error(result)
                    task_state.add_tool_call(tool_name, {}, False, result, iterations)
                append_tool_result(messages, tool_call.id, result)
                continue

            print(f"    TOOL {tool_name}({args})")

            allowed, reason = check_permissions(tool_name, args, config)

            if not allowed:
                result = f"Blocked by policies: {reason}"
                print(f"    BLOCKED {result}")
                if task_state:
                    task_state.add_tool_call(tool_name, args, False, result, iterations)
                if trace:
                    trace.record_tool_call(
                        tool_name=tool_name,
                        args=args,
                        allowed=False,
                        result=result,
                        iteration=iterations,
                        latency_seconds=0.0,
                    )
                append_tool_result(messages, tool_call.id, result)
                continue

            needs_approval = supervision and tool_name in TOOLS_WITH_SUPERVISION
            needs_approval = needs_approval or requires_approval(tool_name, args, config)

            if needs_approval:
                approved = ask_permission(tool_name, args)

                if not approved:
                    result = f"Action '{tool_name}' rejected by user."
                    print("    REJECTED")
                    if task_state:
                        task_state.add_tool_call(tool_name, args, False, result, iterations)
                    if trace:
                        trace.record_tool_call(
                            tool_name=tool_name,
                            args=args,
                            allowed=False,
                            result=result,
                            iteration=iterations,
                            latency_seconds=0.0,
                        )
                    append_tool_result(messages, tool_call.id, result)
                    continue

            function = TOOL_FUNCTIONS.get(tool_name)

            if not function:
                result = f"Unknown tool: {tool_name}"
            else:
                execution_args = normalize_tool_args(tool_name, args, config)
                tool_started_at = time.perf_counter()
                result = function(**execution_args)
                tool_latency_seconds = time.perf_counter() - tool_started_at

            if task_state:
                task_state.add_tool_call(tool_name, args, True, str(result), iterations)

            if trace:
                trace.record_tool_call(
                    tool_name=tool_name,
                    args=args,
                    allowed=True,
                    result=str(result),
                    iteration=iterations,
                    latency_seconds=tool_latency_seconds if function else 0.0,
                )

            append_tool_result(messages, tool_call.id, str(result))


def append_tool_result(messages: list[dict], tool_call_id: str, content: str) -> None:
    messages.append(
        {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": content,
        }
    )
