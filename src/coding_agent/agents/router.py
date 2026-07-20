from __future__ import annotations

from typing import Any

from coding_agent.agents.route_classifier import LlmRouteClassifier
from coding_agent.agents.route_models import RoutePlan
from coding_agent.agents.route_parser import RoutePlanParser
from coding_agent.agents.route_policy import RoutePlanBuilder


class SubagentRouter:
    """Coordinates LLM classification, route parsing, and route policy."""

    def __init__(
        self,
        classifier: LlmRouteClassifier | None = None,
        parser: RoutePlanParser | None = None,
        builder: RoutePlanBuilder | None = None,
    ):
        self.classifier = classifier or LlmRouteClassifier()
        self.parser = parser or RoutePlanParser()
        self.builder = builder or RoutePlanBuilder()

    def route(
        self,
        request: str,
        llm_client: Any | None = None,
        trace: Any | None = None,
    ) -> RoutePlan:
        try:
            classification = self.classifier.classify(
                request,
                llm_client=llm_client,
                trace=trace,
            )
            parsed_route = self.parser.parse(classification)
            return self.builder.build(parsed_route)
        except Exception as error:
            record_router_error(trace, error)
            raise


def record_router_error(trace: Any | None, error: Exception) -> None:
    if trace and hasattr(trace, "record_error"):
        trace.record_error("subagent_router", error)


def format_route_plan(plan: RoutePlan) -> str:
    selected = ", ".join(
        f"{entry.spec.name} ({entry.reason})"
        for entry in plan.selected
    )
    skipped = ", ".join(
        f"{entry.name} ({entry.reason})"
        for entry in plan.skipped
    )

    return (
        f"Subagent route selected: {selected or 'none'}. "
        f"Skipped: {skipped or 'none'}."
    )


__all__ = ["SubagentRouter", "format_route_plan"]
