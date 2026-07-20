from __future__ import annotations

import json
from typing import Any

from coding_agent.agents.route_models import (
    ParsedRoute,
    RouteClassificationError,
    RouteItem,
)


class RoutePlanParser:
    """Parses the LLM router JSON without applying routing policy."""

    def parse(self, output: str) -> ParsedRoute:
        try:
            data = json.loads(extract_json_object(output))
        except (TypeError, json.JSONDecodeError, ValueError) as error:
            raise RouteClassificationError(str(error)) from error

        return ParsedRoute(
            selected=parse_route_items(
                data.get("selected", []),
                default_reason="selected by LLM router",
            ),
            skipped=parse_route_items(
                data.get("skipped", []),
                default_reason="not selected by LLM router",
            ),
        )


def extract_json_object(text: str) -> str:
    stripped = text.strip()

    if stripped.startswith("```"):
        stripped = stripped.strip("`").strip()
        if stripped.lower().startswith("json"):
            stripped = stripped[4:].strip()

    start = stripped.find("{")
    end = stripped.rfind("}")

    if start == -1 or end == -1 or end < start:
        raise ValueError("router LLM did not return a JSON object")

    return stripped[start : end + 1]


def parse_route_items(
    items: Any,
    default_reason: str,
) -> tuple[RouteItem, ...]:
    if not isinstance(items, list):
        return ()

    return tuple(
        item
        for item in (
            route_item_from_raw(raw_item, default_reason)
            for raw_item in items
        )
        if item.name
    )


def route_item_from_raw(
    item: Any,
    default_reason: str,
) -> RouteItem:
    if isinstance(item, str):
        return RouteItem(item.strip().lower(), default_reason)

    if not isinstance(item, dict):
        return RouteItem("", default_reason)

    name = str(item.get("name", "")).strip().lower()
    reason = str(item.get("reason") or default_reason).strip()
    return RouteItem(name, reason)
