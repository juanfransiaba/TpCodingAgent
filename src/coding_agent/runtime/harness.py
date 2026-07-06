import json
import time
from collections.abc import Callable
from dataclasses import dataclass
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


@dataclass
class Harness:
    config: dict
    supervision: bool
    task_state: TaskState | None
    trace: Any
    loop_guard: LoopGuard
    tool_functions: dict[str, Callable[..., Any]]
    tools_with_supervision: set[str]
    verbose: bool


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
    harness = Harness(
        config=config,
        supervision=supervision,
        task_state=task_state,
        trace=trace,
        loop_guard=loop_guard,
        tool_functions=active_tool_functions,
        tools_with_supervision=active_tools_with_supervision,
        verbose=verbose,
    )
    model = getattr(active_llm_client, "model", MODEL)

    while True:
        iteration_limit_result = stop_if_iteration_limit_reached(
            iterations,
            max_iterations,
            harness,
        )

        if iteration_limit_result:
            return iteration_limit_result

        iterations += 1
        prepare_iteration(iterations, harness)
        response = call_llm(
            active_llm_client,
            messages,
            active_tools,
            model,
            iterations,
            harness,
        )
        msg = response.choices[0].message

        messages.append(build_assistant_message(msg))

        if not msg.tool_calls:
            log(" -> final response", verbose=harness.verbose)
            if harness.task_state:
                harness.task_state.add_agent_result("llm_agent", msg.content or "")
            return msg.content or "", iterations

        log(
            f" -> wants to use {len(msg.tool_calls)} tool(s)",
            verbose=harness.verbose,
        )

        handle_tool_calls(msg.tool_calls, messages, iterations, harness)


def stop_if_iteration_limit_reached(
    iterations: int,
    max_iterations: int | None,
    harness: Harness,
) -> tuple[str, int] | None:
    if max_iterations is None or iterations < max_iterations:
        return None

    result = f"Stopped by iteration limit: max_iterations={max_iterations}"
    log(f" -> {result}", verbose=harness.verbose)

    if harness.task_state:
        harness.task_state.mark_blocked(result)
        harness.task_state.add_agent_result("llm_agent", result, status="blocked")

    if harness.trace:
        harness.trace.record_error("max_iterations", result)

    return result, iterations


def prepare_iteration(iterations: int, harness: Harness) -> None:
    if harness.task_state:
        harness.task_state.set_iterations(iterations)
        harness.task_state.add_progress(f"Calling LLM for iteration {iterations}.")

    log(
        f"  [iteration {iterations}] Calling LLM...",
        verbose=harness.verbose,
        end="",
        flush=True,
    )


def call_llm(
    llm_client,
    messages: list[dict],
    tools: list[dict],
    model: str,
    iterations: int,
    harness: Harness,
):
    started_at = time.perf_counter()

    try:
        response = llm_client.chat(
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )
    except Exception as error:
        latency_seconds = time.perf_counter() - started_at
        if harness.trace:
            harness.trace.record_llm_call(
                iteration=iterations,
                messages=messages,
                model=model,
                output="",
                latency_seconds=latency_seconds,
                usage=None,
                error=str(error),
            )
        raise

    latency_seconds = time.perf_counter() - started_at
    msg = response.choices[0].message

    if harness.trace:
        harness.trace.record_llm_call(
            iteration=iterations,
            messages=messages,
            model=model,
            output=msg.content or "",
            latency_seconds=latency_seconds,
            usage=getattr(response, "usage", None),
        )

    return response


def build_assistant_message(msg) -> dict:
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

    return assistant_msg


def handle_tool_calls(
    tool_calls,
    messages: list[dict],
    iterations: int,
    harness: Harness,
) -> None:
    for tool_call in tool_calls:
        handle_tool_call(tool_call, messages, iterations, harness)


def handle_tool_call(
    tool_call,
    messages: list[dict],
    iterations: int,
    harness: Harness,
) -> None:
    tool_name = tool_call.function.name
    args = parse_tool_arguments(tool_call, messages, iterations, harness)

    if args is None:
        return

    log(f"    TOOL {tool_name}({args})", verbose=harness.verbose)

    if not record_policy_result(tool_call, tool_name, args, messages, iterations, harness):
        return

    if not record_approval_result(tool_call, tool_name, args, messages, iterations, harness):
        return

    function = harness.tool_functions.get(tool_name)
    result, latency_seconds = execute_tool_function(tool_name, args, function, harness)

    if harness.task_state:
        harness.task_state.add_tool_call(tool_name, args, True, str(result), iterations)

    result = apply_loop_guard(tool_name, args, str(result), harness)
    record_trace_tool_call(
        tool_name=tool_name,
        args=args,
        allowed=True,
        result=str(result),
        iteration=iterations,
        latency_seconds=latency_seconds,
        harness=harness,
    )
    append_tool_result(messages, tool_call.id, str(result))


def parse_tool_arguments(
    tool_call,
    messages: list[dict],
    iterations: int,
    harness: Harness,
) -> dict[str, Any] | None:
    tool_name = tool_call.function.name

    try:
        return json.loads(tool_call.function.arguments)
    except json.JSONDecodeError as error:
        result = f"Invalid tool arguments: {error}"
        log(f"    ERROR {tool_name}: {result}", verbose=harness.verbose)

        if harness.task_state:
            harness.task_state.add_error(result)
            harness.task_state.add_tool_call(tool_name, {}, False, result, iterations)

        append_tool_result(messages, tool_call.id, result)
        return None


def record_policy_result(
    tool_call,
    tool_name: str,
    args: dict[str, Any],
    messages: list[dict],
    iterations: int,
    harness: Harness,
) -> bool:
    allowed, reason = check_permissions(tool_name, args, harness.config)

    if allowed:
        return True

    result = f"Blocked by policies: {reason}"
    log(f"    BLOCKED {result}", verbose=harness.verbose)

    if harness.task_state:
        harness.task_state.add_tool_call(tool_name, args, False, result, iterations)

    record_trace_tool_call(
        tool_name=tool_name,
        args=args,
        allowed=False,
        result=result,
        iteration=iterations,
        latency_seconds=0.0,
        harness=harness,
    )
    append_tool_result(messages, tool_call.id, result)
    return False


def record_approval_result(
    tool_call,
    tool_name: str,
    args: dict[str, Any],
    messages: list[dict],
    iterations: int,
    harness: Harness,
) -> bool:
    needs_approval = (
        harness.supervision and tool_name in harness.tools_with_supervision
    )
    needs_approval = needs_approval or requires_approval(
        tool_name,
        args,
        harness.config,
    )

    if not needs_approval or ask_permission(tool_name, args):
        return True

    result = f"Action '{tool_name}' rejected by user."
    log("    REJECTED", verbose=harness.verbose)

    if harness.task_state:
        harness.task_state.add_tool_call(tool_name, args, False, result, iterations)

    record_trace_tool_call(
        tool_name=tool_name,
        args=args,
        allowed=False,
        result=result,
        iteration=iterations,
        latency_seconds=0.0,
        harness=harness,
    )
    append_tool_result(messages, tool_call.id, result)
    return False


def execute_tool_function(
    tool_name: str,
    args: dict[str, Any],
    function: Callable[..., Any] | None,
    harness: Harness,
) -> tuple[str, float]:
    if not function:
        return f"Unknown tool: {tool_name}", 0.0

    execution_args = normalize_tool_args(tool_name, args, harness.config)
    started_at = time.perf_counter()

    try:
        result = function(**execution_args)
    except Exception as error:
        result = f"Tool execution error in {tool_name}: {error}"
        if harness.task_state:
            harness.task_state.add_error(result)
        if harness.trace:
            harness.trace.record_error(f"tool_{tool_name}", error)

    return str(result), time.perf_counter() - started_at


def apply_loop_guard(
    tool_name: str,
    args: dict[str, Any],
    result: str,
    harness: Harness,
) -> str:
    repeated, loop_message = harness.loop_guard.record_tool_result(
        tool_name,
        args,
        result,
    )

    if not repeated:
        return result

    if harness.task_state:
        harness.task_state.add_observation(loop_message)

    if harness.trace:
        harness.trace.record_event(
            "loop_guard",
            metadata={
                "tool_name": tool_name,
                "args": args,
                "message": loop_message,
            },
        )

    return f"{result}\n\nLoop guard: {loop_message}"


def record_trace_tool_call(
    tool_name: str,
    args: dict[str, Any],
    allowed: bool,
    result: str,
    iteration: int,
    latency_seconds: float,
    harness: Harness,
) -> None:
    if not harness.trace:
        return

    harness.trace.record_tool_call(
        tool_name=tool_name,
        args=args,
        allowed=allowed,
        result=result,
        iteration=iteration,
        latency_seconds=latency_seconds,
    )


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
