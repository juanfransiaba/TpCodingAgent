from __future__ import annotations

from dataclasses import dataclass

from coding_agent.agents.specs import SUBAGENT_SPECS, SubagentSpec


ROUTE_ORDER = tuple(SUBAGENT_SPECS.keys())


class RouteClassificationError(RuntimeError):
    """Raised when the router cannot obtain a valid LLM route."""


@dataclass(frozen=True)
class RouteItem:
    name: str
    reason: str


@dataclass(frozen=True)
class ParsedRoute:
    selected: tuple[RouteItem, ...]
    skipped: tuple[RouteItem, ...]


@dataclass(frozen=True)
class RoutedSubagent:
    spec: SubagentSpec
    reason: str


@dataclass(frozen=True)
class SkippedSubagent:
    name: str
    reason: str


@dataclass(frozen=True)
class RoutePlan:
    selected: tuple[RoutedSubagent, ...]
    skipped: tuple[SkippedSubagent, ...]

    @property
    def specs(self) -> list[SubagentSpec]:
        return [entry.spec for entry in self.selected]

    @property
    def selected_names(self) -> list[str]:
        return [entry.spec.name for entry in self.selected]

    def reason_for(self, subagent_name: str) -> str:
        for entry in self.selected:
            if entry.spec.name == subagent_name:
                return entry.reason

        return ""
