from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


VALID_STATUSES = {"completed", "blocked", "skipped", "error"}
REVIEWER_RECOMMENDATIONS = {"approved", "changes_requested", "blocked"}
WORKER_RECOMMENDATIONS = {"continue", "blocked"}
DEFAULT_RECOMMENDATIONS = {
    "explorer": "continue",
    "researcher": "continue",
    "implementer": "continue",
    "tester": "continue",
    "reviewer": "approved",
}


@dataclass(frozen=True)
class SubagentRunResult:
    agent_name: str
    summary: str
    status: str = "completed"
    evidence: tuple[str, ...] = field(default_factory=tuple)
    files_changed: tuple[str, ...] = field(default_factory=tuple)
    blockers: tuple[str, ...] = field(default_factory=tuple)
    recommendation: str = "continue"
    raw_response: str = ""


def parse_subagent_result(agent_name: str, response: str) -> SubagentRunResult:
    payload = parse_json_object(response)

    if payload is None:
        return fallback_result(agent_name, response)

    status = normalize_choice(payload.get("status"), VALID_STATUSES, "completed")
    summary = str(payload.get("summary") or response).strip()
    evidence = normalize_string_tuple(payload.get("evidence"))
    files_changed = normalize_string_tuple(payload.get("files_changed"))
    blockers = normalize_string_tuple(payload.get("blockers"))
    recommendation = normalize_recommendation(
        agent_name=agent_name,
        value=payload.get("recommendation"),
        status=status,
        blockers=blockers,
        response=response,
    )

    return SubagentRunResult(
        agent_name=agent_name,
        summary=summary,
        status=status,
        evidence=evidence,
        files_changed=files_changed,
        blockers=blockers,
        recommendation=recommendation,
        raw_response=response,
    )


def fallback_result(agent_name: str, response: str) -> SubagentRunResult:
    summary = response.strip()
    status = "completed"
    recommendation = infer_recommendation(
        agent_name=agent_name,
        status=status,
        blockers=(),
        response=response,
    )

    return SubagentRunResult(
        agent_name=agent_name,
        summary=summary,
        status=status,
        recommendation=recommendation,
        raw_response=response,
    )


def parse_json_object(text: str) -> dict[str, Any] | None:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return parse_embedded_json_object(text)

    return payload if isinstance(payload, dict) else None


def parse_embedded_json_object(text: str) -> dict[str, Any] | None:
    decoder = json.JSONDecoder()

    for index, character in enumerate(text):
        if character != "{":
            continue

        try:
            payload, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue

        if isinstance(payload, dict):
            return payload

    return None


def normalize_choice(value: Any, allowed: set[str], default: str) -> str:
    normalized = str(value or "").strip().lower()
    return normalized if normalized in allowed else default


def normalize_string_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()

    if isinstance(value, str):
        value = [value]

    if not isinstance(value, list):
        return (str(value).strip(),) if str(value).strip() else ()

    return tuple(
        item
        for item in (str(entry).strip() for entry in value)
        if item
    )


def normalize_recommendation(
    agent_name: str,
    value: Any,
    status: str,
    blockers: tuple[str, ...],
    response: str,
) -> str:
    if agent_name == "reviewer":
        normalized = normalize_choice(value, REVIEWER_RECOMMENDATIONS, "")
        if normalized:
            return normalized

    else:
        normalized = normalize_choice(value, WORKER_RECOMMENDATIONS, "")
        if normalized:
            return normalized

    return infer_recommendation(
        agent_name=agent_name,
        status=status,
        blockers=blockers,
        response=response,
    )


def infer_recommendation(
    agent_name: str,
    status: str,
    blockers: tuple[str, ...],
    response: str,
) -> str:
    normalized_response = response.lower()

    if status in ("blocked", "error"):
        return "blocked"

    if agent_name == "reviewer":
        if "changes_requested" in normalized_response or blockers:
            return "changes_requested"
        if "blocked" in normalized_response:
            return "blocked"
        return "approved"

    if blockers:
        return "blocked"

    return DEFAULT_RECOMMENDATIONS.get(agent_name, "continue")
