import json
import time
from collections.abc import Callable
from typing import Any

from coding_agent.core.task_state import TaskState
from coding_agent.llm.client import MODEL, default_llm_client
from coding_agent.runtime.loop_guard import LoopGuard
from coding_agent.security.permissions import (
    check_permissions,
    normalize_tool_args,
    requires_approval,
)
from coding_agent.security.supervision import ask_permission
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
    llm_client=None,
    tools: list[dict] | None = None,
    tool_functions: dict[str, Callable[..., Any]] | None = None,
    tools_with_supervision: set[str] | None = None,
    verbose: bool = True,
    max_iterations: int | None = None,
) -> tuple[str, int]:
    """Runs the inner loop: LLM -> tool calls -> tool results -> LLM."""

    iterations = 0
    loop_guard = LoopGuard()
    active_llm_client = llm_client or default_llm_client
    active_tools = TOOLS if tools is None else tools
    active_tool_functions = TOOL_FUNCTIONS if tool_functions is None else tool_functions
    active_tools_with_supervision = (
        TOOLS_WITH_SUPERVISION
        if tools_with_supervision is None
        else tools_with_supervision
    )
    model = getattr(active_llm_client, "model", MODEL)

    while True:
        if max_iterations is not None and iterations >= max_iterations:
            result = f"Stopped by iteration limit: max_iterations={max_iterations}"
            log(f" -> {result}", verbose=verbose)

            if task_state:
                task_state.mark_blocked(result)
                task_state.add_agent_result("main_agent", result, status="blocked")

            if trace:
                trace.record_error("max_iterations", result)

            return result, iterations

        iterations += 1
        if task_state:
            task_state.set_iterations(iterations)
            task_state.add_progress(f"Calling LLM for iteration {iterations}.")

        log(
            f"  [iteration {iterations}] Calling LLM...",
            verbose=verbose,
            end="",
            flush=True,
        )

        llm_started_at = time.perf_counter()

        try:
            response = active_llm_client.chat(
                messages=messages,
                tools=active_tools,
                tool_choice="auto",
            )
        except Exception as error:
            latency_seconds = time.perf_counter() - llm_started_at
            if trace:
                trace.record_llm_call(
                    iteration=iterations,
                    messages=messages,
                    model=model,
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
                model=model,
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
            log(" -> final response", verbose=verbose)
            if task_state:
                task_state.add_agent_result("main_agent", msg.content or "")
            return msg.content or "", iterations

        log(
            f" -> wants to use {len(msg.tool_calls)} tool(s)",
            verbose=verbose,
        )

        for tool_call in msg.tool_calls:
            tool_name = tool_call.function.name

            try:
                args = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError as error:
                result = f"Invalid tool arguments: {error}"
                log(f"    ERROR {tool_name}: {result}", verbose=verbose)
                if task_state:
                    task_state.add_error(result)
                    task_state.add_tool_call(tool_name, {}, False, result, iterations)
                append_tool_result(messages, tool_call.id, result)
                continue

            log(f"    TOOL {tool_name}({args})", verbose=verbose)

            allowed, reason = check_permissions(tool_name, args, config)

            if not allowed:
                result = f"Blocked by policies: {reason}"
                log(f"    BLOCKED {result}", verbose=verbose)
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

            needs_approval = supervision and tool_name in active_tools_with_supervision
            needs_approval = needs_approval or requires_approval(tool_name, args, config)

            if needs_approval:
                approved = ask_permission(tool_name, args)

                if not approved:
                    result = f"Action '{tool_name}' rejected by user."
                    log("    REJECTED", verbose=verbose)
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

            function = active_tool_functions.get(tool_name)

            if not function:
                result = f"Unknown tool: {tool_name}"
                tool_latency_seconds = 0.0
            else:
                execution_args = normalize_tool_args(tool_name, args, config)
                tool_started_at = time.perf_counter()
                try:
                    result = function(**execution_args)
                except Exception as error:
                    result = f"Tool execution error in {tool_name}: {error}"
                    if task_state:
                        task_state.add_error(result)
                    if trace:
                        trace.record_error(f"tool_{tool_name}", error)
                tool_latency_seconds = time.perf_counter() - tool_started_at

            if task_state:
                task_state.add_tool_call(tool_name, args, True, str(result), iterations)

            repeated, loop_message = loop_guard.record_tool_result(
                tool_name,
                args,
                str(result),
            )

            if repeated:
                result = f"{result}\n\nLoop guard: {loop_message}"
                if task_state:
                    task_state.add_observation(loop_message)
                if trace:
                    trace.record_event(
                        "loop_guard",
                        metadata={
                            "tool_name": tool_name,
                            "args": args,
                            "message": loop_message,
                        },
                    )

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


def log(
    message: str,
    verbose: bool,
    end: str = "\n",
    flush: bool = False,
) -> None:
    if verbose:
        print(message, end=end, flush=flush)
