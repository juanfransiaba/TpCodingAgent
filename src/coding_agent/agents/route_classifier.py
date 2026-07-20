from __future__ import annotations

import time
from typing import Any

from coding_agent.agents.route_models import RouteClassificationError
from coding_agent.agents.specs import SUBAGENT_SPECS


ROUTER_MODEL_ITERATION = 0


class LlmRouteClassifier:
    """Calls the LLM once to classify a user request into subagent roles."""

    def classify(
        self,
        request: str,
        llm_client: Any | None,
        trace: Any | None = None,
    ) -> str:
        if not llm_client:
            raise RouteClassificationError("SubagentRouter requires an LLM client.")

        messages = build_router_messages(request)
        started_at = time.perf_counter()
        model = getattr(llm_client, "model", "unknown")
        output = ""
        usage = None

        try:
            response = llm_client.chat(messages=messages)
            output = response.choices[0].message.content or ""
            usage = getattr(response, "usage", None)
        except Exception as error:
            record_router_llm_call(
                trace=trace,
                messages=messages,
                model=model,
                output=output,
                latency_seconds=time.perf_counter() - started_at,
                usage=usage,
                error=str(error),
            )
            raise

        record_router_llm_call(
            trace=trace,
            messages=messages,
            model=model,
            output=output,
            latency_seconds=time.perf_counter() - started_at,
            usage=usage,
            error=None,
        )
        return output


def build_router_messages(request: str) -> list[dict[str, str]]:
    agents = "\n".join(
        (
            f"- {spec.name}: {spec.responsibility} "
            f"Tools: {', '.join(spec.allowed_tools)}."
        )
        for spec in SUBAGENT_SPECS.values()
    )

    system_content = f"""
You classify user requests for a coding agent. Select the smallest useful set of
subagents for the request. Return only valid JSON.

Available subagents:
{agents}

Routing rules:
- Use explorer when repository context, file inspection, architecture, or code evidence is needed.
- Use researcher when external technical knowledge, RAG, memory, documentation, or web evidence is needed.
- Use implementer only when concrete file changes are requested.
- Use tester when checks, tests, builds, linting, or validation are needed.
- Use reviewer when implementation, validation, review, or diff acceptance is needed.
- For implementation work, include explorer, implementer, tester, and reviewer.
- Preserve this execution order when multiple roles are selected:
  explorer, researcher, implementer, tester, reviewer.

JSON schema:
{{
  "selected": [
    {{"name": "explorer|researcher|implementer|tester|reviewer", "reason": "short reason"}}
  ],
  "skipped": [
    {{"name": "explorer|researcher|implementer|tester|reviewer", "reason": "short reason"}}
  ]
}}
""".strip()

    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": request},
    ]


def record_router_llm_call(
    trace: Any | None,
    messages: list[dict[str, str]],
    model: str,
    output: str,
    latency_seconds: float,
    usage: Any = None,
    error: str | None = None,
) -> None:
    if not trace or not hasattr(trace, "record_llm_call"):
        return

    trace.record_llm_call(
        iteration=ROUTER_MODEL_ITERATION,
        messages=messages,
        model=model,
        output=output,
        latency_seconds=latency_seconds,
        usage=usage,
        error=error,
        agent_name="router",
        observation_name="router-classification",
    )
