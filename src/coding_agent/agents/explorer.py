from pathlib import Path

from coding_agent.core.permissions import check_permissions
from coding_agent.core.task_state import TaskState
from coding_agent.prompts.explorer_prompt import EXPLORER_PROMPT

MAX_FILES_TO_REPORT = 40
METADATA_FILES = (
    "README.md",
    "SPEC.md",
    "pyproject.toml",
    "requirements.txt",
    "package.json",
    "agent.config.yaml",
)


def run(task_state: TaskState, config: dict) -> str:
    """Explore the configured workspace and summarize repository evidence."""

    workspace = Path(config.get("workspace", ".")).resolve()

    if not workspace.exists():
        summary = (
            f"Workspace does not exist yet: {workspace}. "
            "The main agent should ask for setup or create it only if requested."
        )
        task_state.add_agent_result("explorer", summary, status="blocked")
        return summary

    files = collect_files(workspace)
    metadata = collect_metadata(workspace, config)

    summary_lines = [
        "Explorer summary:",
        f"- Workspace: {workspace}",
        f"- Files found: {len(files)}",
    ]

    if files:
        summary_lines.append("- Relevant files:")
        summary_lines.extend(f"  - {path}" for path in files[:MAX_FILES_TO_REPORT])

    if metadata:
        summary_lines.append("- Metadata evidence:")
        summary_lines.extend(f"  - {item}" for item in metadata)

    summary_lines.append("- Role instruction:")
    summary_lines.append(EXPLORER_PROMPT.strip())

    summary = "\n".join(summary_lines)
    task_state.add_agent_result("explorer", summary)
    task_state.add_observation(f"Explorer inspected workspace {workspace}.")
    return summary


def collect_files(workspace: Path) -> list[str]:
    files: list[str] = []

    for path in sorted(workspace.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts:
            files.append(path.relative_to(workspace).as_posix())

    return files


def collect_metadata(workspace: Path, config: dict) -> list[str]:
    metadata: list[str] = []

    for name in METADATA_FILES:
        candidate = workspace / name

        if not candidate.exists() or not candidate.is_file():
            continue

        allowed, reason = check_permissions(
            "read_file",
            {"path": candidate.relative_to(workspace).as_posix()},
            config,
        )

        if not allowed:
            metadata.append(f"{name}: blocked by policy ({reason})")
            continue

        preview = candidate.read_text(encoding="utf-8", errors="replace")[:500]
        metadata.append(f"{name}: {preview.replace(chr(10), ' ')[:250]}")

    return metadata
