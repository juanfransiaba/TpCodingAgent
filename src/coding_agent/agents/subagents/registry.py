from __future__ import annotations

from coding_agent.agents.subagents.base import BaseSubagent
from coding_agent.agents.subagents.explorer import ExplorerSubagent
from coding_agent.agents.subagents.implementer import ImplementerSubagent
from coding_agent.agents.subagents.researcher import ResearcherSubagent
from coding_agent.agents.subagents.reviewer import ReviewerSubagent
from coding_agent.agents.subagents.tester import TesterSubagent


class SubagentRegistry:
    def __init__(self, subagents: dict[str, BaseSubagent] | None = None):
        self.subagents = subagents or default_subagents()

    def get(self, name: str) -> BaseSubagent:
        try:
            return self.subagents[name]
        except KeyError as error:
            raise KeyError(f"Unknown subagent: {name}") from error


def default_subagents() -> dict[str, BaseSubagent]:
    subagents: tuple[BaseSubagent, ...] = (
        ExplorerSubagent(),
        ResearcherSubagent(),
        ImplementerSubagent(),
        TesterSubagent(),
        ReviewerSubagent(),
    )
    return {subagent.name: subagent for subagent in subagents}
