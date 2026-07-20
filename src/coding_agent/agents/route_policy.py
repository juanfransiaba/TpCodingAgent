from __future__ import annotations

from coding_agent.agents.route_models import (
    ROUTE_ORDER,
    ParsedRoute,
    RouteClassificationError,
    RoutePlan,
    RoutedSubagent,
    SkippedSubagent,
)
from coding_agent.agents.specs import SUBAGENT_SPECS


class RoutePlanBuilder:
    """Validates parsed route items and applies routing invariants."""

    def build(self, parsed_route: ParsedRoute) -> RoutePlan:
        selected = known_reasons(parsed_route.selected)

        if not selected:
            raise RouteClassificationError(
                "router LLM returned no valid selected subagents"
            )

        selected = apply_route_invariants(selected)
        skipped = known_reasons(parsed_route.skipped)
        return build_route_plan(selected, skipped)


def known_reasons(items) -> dict[str, str]:
    reasons: dict[str, str] = {}

    for item in items:
        if item.name in SUBAGENT_SPECS:
            reasons[item.name] = item.reason

    return reasons


def apply_route_invariants(selected: dict[str, str]) -> dict[str, str]:
    selected = dict(selected)

    if "implementer" in selected:
        selected.setdefault(
            "explorer",
            "implementation work requires repository context first",
        )
        selected.setdefault(
            "tester",
            "implementation work should be validated after writes",
        )
        selected.setdefault(
            "reviewer",
            "implementation work should be reviewed against the request",
        )

    if "tester" in selected:
        selected.setdefault(
            "reviewer",
            "validation output should be reviewed against the request",
        )

    return {
        name: selected[name]
        for name in ROUTE_ORDER
        if name in selected
    }


def build_route_plan(
    selected: dict[str, str],
    skipped_reasons: dict[str, str],
) -> RoutePlan:
    return RoutePlan(
        selected=tuple(
            RoutedSubagent(
                spec=SUBAGENT_SPECS[name],
                reason=selected[name],
            )
            for name in ROUTE_ORDER
            if name in selected
        ),
        skipped=tuple(
            SkippedSubagent(
                name=name,
                reason=skipped_reasons.get(name, "not selected by LLM router"),
            )
            for name in ROUTE_ORDER
            if name not in selected
        ),
    )
