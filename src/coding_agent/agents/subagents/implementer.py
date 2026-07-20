from __future__ import annotations

from coding_agent.agents.subagents.base import BaseSubagent


class ImplementerSubagent(BaseSubagent):
    spec_name = "implementer"
    marks_implementation_attempted = True
