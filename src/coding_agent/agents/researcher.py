from pathlib import Path

from coding_agent.core.permissions import check_permissions
from coding_agent.core.task_state import TaskState
from coding_agent.memory.project_memory import ProjectMemory
from coding_agent.prompts.researcher_prompt import RESEARCHER_PROMPT

DOC_PATTERNS = ("README.md", "SPEC.md", "docs")


def run(
    task_state: TaskState,
    config: dict,
    memory: ProjectMemory | None = None,
) -> str:
    """Collect local documentation sources and identify research gaps."""

    workspace = Path(config.get("workspace", ".")).resolve()
    sources = find_local_sources(workspace, config)

    for source in sources:
        task_state.add_source(
            kind="repo",
            title=source["title"],
            location=source["location"],
            summary=source["summary"],
        )

    summary_lines = [
        "Researcher summary:",
        f"- Local documentation sources found: {len(sources)}",
    ]

    if memory:
        memory_context = memory.get_relevant_context()
        summary_lines.append("- Persistent memory loaded: yes")
        summary_lines.append(memory_context)
    else:
        summary_lines.append("- Persistent memory loaded: no")

    if sources:
        summary_lines.extend(
            f"  - {source['location']}: {source['summary']}"
            for source in sources
        )
    else:
        summary_lines.append(
            "- No local docs found in the configured workspace. Use RAG when available, then web fallback if evidence is insufficient."
        )

    summary_lines.append("- Role instruction:")
    summary_lines.append(RESEARCHER_PROMPT.strip())

    summary = "\n".join(summary_lines)
    task_state.add_agent_result("researcher", summary)
    return summary


def find_local_sources(workspace: Path, config: dict) -> list[dict[str, str]]:
    if not workspace.exists():
        return []

    sources: list[dict[str, str]] = []

    for path in sorted(workspace.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts:
            continue

        relative_path = path.relative_to(workspace).as_posix()

        if not is_documentation_path(relative_path):
            continue

        allowed, reason = check_permissions(
            "read_file",
            {"path": relative_path},
            config,
        )

        if not allowed:
            sources.append(
                {
                    "title": path.name,
                    "location": relative_path,
                    "summary": f"Blocked by policy: {reason}",
                }
            )
            continue

        preview = path.read_text(encoding="utf-8", errors="replace")[:300]
        sources.append(
            {
                "title": path.name,
                "location": relative_path,
                "summary": preview.replace("\n", " ")[:180],
            }
        )

    return sources


def is_documentation_path(relative_path: str) -> bool:
    normalized = relative_path.lower()

    return (
        normalized.endswith(".md")
        or normalized.startswith("docs/")
        or any(pattern.lower() in normalized for pattern in DOC_PATTERNS)
    )
