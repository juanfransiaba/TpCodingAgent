from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class LoopGuard:
    """Detects repeated tool calls that are not producing new information."""

    max_repetitions: int = 3
    seen: dict[str, int] = field(default_factory=dict)

    def record_tool_result(
        self,
        tool_name: str,
        args: dict[str, Any],
        result: str,
    ) -> tuple[bool, str]:
        fingerprint = build_fingerprint(tool_name, args, result)
        self.seen[fingerprint] = self.seen.get(fingerprint, 0) + 1
        count = self.seen[fingerprint]

        if count < self.max_repetitions:
            return False, ""

        return (
            True,
            (
                f"Repeated action detected: {tool_name} returned the same result "
                f"{count} times with equivalent arguments. Change strategy, use a "
                "different source of evidence, replan, or ask the user for help."
            ),
        )


def build_fingerprint(
    tool_name: str,
    args: dict[str, Any],
    result: str,
) -> str:
    normalized_args = "|".join(
        f"{key}={args[key]}"
        for key in sorted(args)
        if key not in {"content"}
    )
    normalized_result = result.strip()[:500]
    return f"{tool_name}|{normalized_args}|{normalized_result}"
