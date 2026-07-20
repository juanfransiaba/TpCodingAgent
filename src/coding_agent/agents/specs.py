from __future__ import annotations

from dataclasses import dataclass

from coding_agent.prompts.explorer_prompt import EXPLORER_PROMPT
from coding_agent.prompts.implementer_prompt import IMPLEMENTER_PROMPT
from coding_agent.prompts.researcher_prompt import RESEARCHER_PROMPT
from coding_agent.prompts.reviewer_prompt import REVIEWER_PROMPT
from coding_agent.prompts.tester_prompt import TESTER_PROMPT


@dataclass(frozen=True)
class SubagentSpec:
    name: str
    responsibility: str
    prompt: str
    allowed_tools: tuple[str, ...]
    max_iterations: int = 4


SUBAGENT_SPECS: dict[str, SubagentSpec] = {
    "explorer": SubagentSpec(
        name="explorer",
        responsibility=(
            "Understand repository structure, architecture, dependencies, "
            "conventions, and files relevant to the objective."
        ),
        prompt=EXPLORER_PROMPT,
        allowed_tools=(
            "list_files",
            "tree_files",
            "search_code",
            "read_file",
            "search_rag",
            "read_project_memory",
        ),
        max_iterations=8,
    ),
    "researcher": SubagentSpec(
        name="researcher",
        responsibility=(
            "Investigate technical information. Query RAG first and use web "
            "search only when local evidence is insufficient."
        ),
        prompt=RESEARCHER_PROMPT,
        allowed_tools=(
            "search_rag",
            "web_search",
            "read_project_memory",
        ),
    ),
    "implementer": SubagentSpec(
        name="implementer",
        responsibility=(
            "Apply concrete, scoped code changes from Explorer/Researcher "
            "findings. If evidence is missing or the request is ambiguous, "
            "do not write files and explain the blocker."
        ),
        prompt=IMPLEMENTER_PROMPT,
        allowed_tools=(
            "read_file",
            "write_file",
            "list_files",
        ),
        max_iterations=30,
    ),
    "tester": SubagentSpec(
        name="tester",
        responsibility=(
            "Validate changes with real checks such as tests, build, or lint. "
            "If the same action repeats with the same result, stop instead of looping."
        ),
        prompt=TESTER_PROMPT,
        allowed_tools=(
            "run_command",
            "read_file",
        ),
        max_iterations=5,
    ),
    "reviewer": SubagentSpec(
        name="reviewer",
        responsibility=(
            "Review the real diff against the original request and approve or "
            "flag issues. No write permission by design."
        ),
        prompt=REVIEWER_PROMPT,
        allowed_tools=(
            "read_file",
            "run_command",
        ),
        max_iterations=5,
    ),
}
