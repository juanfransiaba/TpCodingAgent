from __future__ import annotations

from collections.abc import Callable
from contextlib import nullcontext
from typing import Any

from coding_agent.agents.results import (
    SubagentRunResult,
    parse_subagent_result,
)
from coding_agent.agents.router import SubagentRouter, format_route_plan
from coding_agent.agents.specs import SubagentSpec
from coding_agent.core.contracts import AgentContext, AgentState
from coding_agent.runtime.harness import run_agent_turn
from coding_agent.tools.tool_registry import (
    supervised_tools_for,
    tool_functions_for,
    tools_for,
)

RunAgentTurnFn = Callable[..., tuple[str, int]]


class AgentPipeline:
    """Routes a task to scoped subagents instead of running a fixed pipeline."""

    def __init__(
        self,
        router: SubagentRouter | None = None,
        run_agent_turn_fn: RunAgentTurnFn = run_agent_turn,
        verbose: bool = False,
        supervision: bool = False,
        trace: Any | None = None,
    ):
        self.router = router or SubagentRouter()
        self.run_agent_turn = run_agent_turn_fn
        self.verbose = verbose
        self.supervision = supervision
        self.trace = trace

    def run(self, state: AgentState, context: AgentContext) -> list[str]:
        route_plan = self.router.route(state.original_request)
        specs = route_plan.specs
        selected_names = ", ".join(route_plan.selected_names)
        state.add_progress(f"Subagent router selected: {selected_names}.")
        state.add_observation(format_route_plan(route_plan))

        summaries: list[str] = []
        implementation_attempted = False
        successful_writes_before_implementation = count_successful_writes(state)

        for spec in specs:
            if should_skip_after_no_changes(
                spec,
                implementation_attempted,
                successful_writes_before_implementation,
                state,
            ):
                skip_reason = (
                    "tester subagent skipped: implementer finished without "
                    "modifying files."
                )
                summary = record_skipped_subagent(spec, state, skip_reason)
                state.add_observation(skip_reason)
                state.add_progress(skip_reason)
                summaries.append(summary)
                continue

            state.add_progress(
                f"{spec.name} subagent started "
                f"({route_plan.reason_for(spec.name)}) with tools: "
                f"{', '.join(spec.allowed_tools)}."
            )
            summary = self.run_subagent(
                spec,
                state,
                context,
                summaries,
                route_plan.reason_for(spec.name),
            )
            summaries.append(summary)
            state.add_progress(f"{spec.name} subagent finished.")

            if spec.name == "implementer":
                implementation_attempted = True

        return summaries

    def run_subagent(
        self,
        spec: SubagentSpec,
        state: AgentState,
        context: AgentContext,
        previous_summaries: list[str],
        route_reason: str = "",
    ) -> str:
        with trace_subagent_context(self.trace, spec, route_reason):
            messages = build_subagent_messages(
                spec,
                state,
                context,
                previous_summaries,
            )
            agent_result_count = len(state.agent_results)

            try:
                response, iterations = self.run_agent_turn(
                    messages=messages,
                    config=context.config,
                    supervision=self.supervision,
                    task_state=state,
                    trace=self.trace,
                    llm_client=context.llm,
                    tools=tools_for(spec.allowed_tools),
                    tool_functions=tool_functions_for(spec.allowed_tools),
                    tools_with_supervision=supervised_tools_for(spec.allowed_tools),
                    verbose=self.verbose,
                    max_iterations=spec.max_iterations,
                    agent_name=spec.name,
                    record_agent_result=False,
                )
                result = parse_subagent_result(spec.name, response)
                summary = format_subagent_summary(spec, result, iterations)
            except Exception as error:
                summary = f"{spec.name} subagent failed: {error}"
                state.add_error(summary)
                state.add_agent_result(
                    spec.name,
                    summary,
                    status="error",
                    blockers=[str(error)],
                    recommendation="blocked",
                )
                return summary

            if len(state.agent_results) == agent_result_count:
                record_subagent_result(state, result)

            if spec.name == "reviewer":
                apply_reviewer_decision(state, result)

            return summary


def build_subagent_messages(
    spec: SubagentSpec,
    state: AgentState,
    context: AgentContext,
    previous_summaries: list[str],
) -> list[dict[str, str]]:
    workspace = context.config.get("workspace", ".")
    allowed_tools = ", ".join(spec.allowed_tools)
    previous_context = (
        "\n\n".join(previous_summaries[-4:])
        or "No previous subagent output."
    )

    system_content = f"""
You are the {spec.name} subagent.

Responsibility:
{spec.responsibility}

Allowed tools:
{allowed_tools}

Rules:
- Use only your allowed tools.
- Stay inside your responsibility. Do not perform another subagent's job.
- Use real tool evidence for repository claims.
- Return exactly one JSON object with:
  "status": "completed|blocked",
  "summary": "concise result",
  "evidence": ["tool-backed facts"],
  "files_changed": ["paths you changed"],
  "blockers": ["unresolved blockers"],
  "recommendation": "{recommendation_options_for(spec.name)}".
- If you cannot produce JSON, return concise text and the harness will wrap it.

Role-specific instructions:
{spec.prompt.strip()}
""".strip()

    user_content = f"""
Original request:
{state.original_request}

Workspace:
{workspace}

Shared state:
- Sources recorded: {len(state.sources)}
- Files modified so far: {", ".join(state.files_modified) or "none"}
- Errors so far: {", ".join(state.errors[-3:]) or "none"}

Previous subagent output:
{previous_context}
""".strip()

    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]


def format_subagent_summary(
    spec: SubagentSpec,
    result: SubagentRunResult,
    iterations: int,
) -> str:
    lines = [
        f"{spec.name} subagent summary:",
        f"- Status: {result.status}",
        f"- Recommendation: {result.recommendation}",
        f"- Tools allowed: {', '.join(spec.allowed_tools)}",
        f"- Iterations: {iterations}",
        f"- Summary: {result.summary or '(empty)'}",
    ]

    if result.evidence:
        lines.append(f"- Evidence: {'; '.join(result.evidence)}")

    if result.files_changed:
        lines.append(f"- Files changed: {', '.join(result.files_changed)}")

    if result.blockers:
        lines.append(f"- Blockers: {'; '.join(result.blockers)}")

    return "\n".join(lines)


def record_subagent_result(
    state: AgentState,
    result: SubagentRunResult,
) -> None:
    state.add_agent_result(
        result.agent_name,
        result.summary,
        status=result.status,
        evidence=list(result.evidence),
        files_changed=list(result.files_changed),
        blockers=list(result.blockers),
        recommendation=result.recommendation,
    )


def record_skipped_subagent(
    spec: SubagentSpec,
    state: AgentState,
    reason: str,
) -> str:
    result = SubagentRunResult(
        agent_name=spec.name,
        summary=reason,
        status="skipped",
        recommendation="continue",
        raw_response=reason,
    )
    record_subagent_result(state, result)
    return format_subagent_summary(spec, result, iterations=0)


def apply_reviewer_decision(
    state: AgentState,
    result: SubagentRunResult,
) -> None:
    if result.recommendation == "approved":
        state.add_observation("reviewer decision: approved")
        return

    if result.recommendation == "changes_requested":
        state.mark_changes_requested(
            f"reviewer decision: changes_requested. {result.summary}"
        )
        return

    if result.recommendation == "blocked":
        state.mark_blocked(f"reviewer decision: blocked. {result.summary}")


def recommendation_options_for(agent_name: str) -> str:
    if agent_name == "reviewer":
        return "approved|changes_requested|blocked"

    return "continue|blocked"


def should_skip_after_no_changes(
    spec: SubagentSpec,
    implementation_attempted: bool,
    successful_writes_before_implementation: int,
    state: AgentState,
) -> bool:
    if spec.name != "tester" or not implementation_attempted:
        return False

    return count_successful_writes(state) == successful_writes_before_implementation


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


def trace_subagent_context(
    trace: Any | None,
    spec: SubagentSpec,
    route_reason: str,
):
    if not trace or not hasattr(trace, "trace_subagent"):
        return nullcontext()

    return trace.trace_subagent(
        spec.name,
        metadata={
            "route_reason": route_reason,
            "responsibility": spec.responsibility,
            "allowed_tools": list(spec.allowed_tools),
            "max_iterations": spec.max_iterations,
        },
    )


def default_pipeline(
    run_agent_turn_fn: RunAgentTurnFn = run_agent_turn,
    verbose: bool = False,
    supervision: bool = False,
    trace: Any | None = None,
) -> AgentPipeline:
    return AgentPipeline(
        run_agent_turn_fn=run_agent_turn_fn,
        verbose=verbose,
        supervision=supervision,
        trace=trace,
    )
