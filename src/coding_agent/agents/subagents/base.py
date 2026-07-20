from __future__ import annotations

from contextlib import nullcontext
from typing import ClassVar

from coding_agent.agents.results import (
    SubagentRunResult,
    parse_subagent_result,
)
from coding_agent.agents.specs import SUBAGENT_SPECS, SubagentSpec
from coding_agent.agents.subagents.context import SubagentRunContext
from coding_agent.core.contracts import AgentState
from coding_agent.tools.tool_registry import (
    supervised_tools_for,
    tool_functions_for,
    tools_for,
)


class BaseSubagent:
    spec_name: ClassVar[str] = ""
    marks_implementation_attempted = False

    def __init__(self, spec: SubagentSpec | None = None):
        if spec is None:
            if not self.spec_name:
                raise ValueError("Subagent must define spec_name or receive a spec.")
            spec = SUBAGENT_SPECS[self.spec_name]

        self.spec = spec

    @property
    def name(self) -> str:
        return self.spec.name

    @property
    def allowed_tools(self) -> tuple[str, ...]:
        return self.spec.allowed_tools

    def should_skip(self, context: SubagentRunContext) -> bool:
        return False

    def skip(self, context: SubagentRunContext) -> str:
        reason = self.skip_reason(context)
        context.state.add_observation(reason)
        context.state.add_progress(reason)
        result = SubagentRunResult(
            agent_name=self.name,
            summary=reason,
            status="skipped",
            recommendation="continue",
            raw_response=reason,
        )
        self.record_result(context.state, result)
        return self.format_summary(result, iterations=0)

    def skip_reason(self, context: SubagentRunContext) -> str:
        return f"{self.name} subagent skipped."

    def run(self, context: SubagentRunContext) -> str:
        with self.trace_context(context):
            messages = self.build_messages(context)
            agent_result_count = len(context.state.agent_results)

            try:
                response, iterations = context.run_agent_turn(
                    messages=messages,
                    config=context.agent_context.config,
                    supervision=context.supervision,
                    task_state=context.state,
                    trace=context.trace,
                    llm_client=context.agent_context.llm,
                    tools=tools_for(self.allowed_tools),
                    tool_functions=tool_functions_for(self.allowed_tools),
                    tools_with_supervision=supervised_tools_for(self.allowed_tools),
                    verbose=context.verbose,
                    max_iterations=self.spec.max_iterations,
                    agent_name=self.name,
                    record_agent_result=False,
                )
                result = parse_subagent_result(self.name, response)
                summary = self.format_summary(result, iterations)
            except Exception as error:
                summary = f"{self.name} subagent failed: {error}"
                context.state.add_error(summary)
                context.state.add_agent_result(
                    self.name,
                    summary,
                    status="error",
                    blockers=[str(error)],
                    recommendation="blocked",
                )
                return summary

            if len(context.state.agent_results) == agent_result_count:
                self.record_result(context.state, result)

            self.after_run(context, result)
            return summary

    def build_messages(self, context: SubagentRunContext) -> list[dict[str, str]]:
        workspace = context.agent_context.config.get("workspace", ".")
        allowed_tools = ", ".join(self.allowed_tools)
        previous_context = (
            "\n\n".join(context.previous_summaries[-4:])
            or "No previous subagent output."
        )

        system_content = f"""
You are the {self.name} subagent.

Responsibility:
{self.spec.responsibility}

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
  "recommendation": "{self.recommendation_options()}".
- If you cannot produce JSON, return concise text and the harness will wrap it.

Role-specific instructions:
{self.spec.prompt.strip()}
""".strip()

        user_content = f"""
Original request:
{context.state.original_request}

Workspace:
{workspace}

Shared state:
- Sources recorded: {len(context.state.sources)}
- Files modified so far: {", ".join(context.state.files_modified) or "none"}
- Errors so far: {", ".join(context.state.errors[-3:]) or "none"}

Previous subagent output:
{previous_context}
""".strip()

        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ]

    def recommendation_options(self) -> str:
        return "continue|blocked"

    def format_summary(
        self,
        result: SubagentRunResult,
        iterations: int,
    ) -> str:
        lines = [
            f"{self.name} subagent summary:",
            f"- Status: {result.status}",
            f"- Recommendation: {result.recommendation}",
            f"- Tools allowed: {', '.join(self.allowed_tools)}",
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

    def record_result(
        self,
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

    def after_run(
        self,
        context: SubagentRunContext,
        result: SubagentRunResult,
    ) -> None:
        return None

    def trace_context(self, context: SubagentRunContext):
        if not context.trace or not hasattr(context.trace, "trace_subagent"):
            return nullcontext()

        return context.trace.trace_subagent(
            self.name,
            metadata={
                "route_reason": context.route_reason,
                "responsibility": self.spec.responsibility,
                "allowed_tools": list(self.allowed_tools),
                "max_iterations": self.spec.max_iterations,
            },
        )
