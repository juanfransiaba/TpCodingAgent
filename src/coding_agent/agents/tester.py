from pathlib import Path

from coding_agent.core.task_state import TaskState
from coding_agent.prompts.tester_prompt import TESTER_PROMPT


def run(task_state: TaskState, config: dict) -> str:
    """Recommend validation commands for the configured workspace."""

    workspace = Path(config.get("workspace", ".")).resolve()
    commands = suggest_commands(workspace)

    summary_lines = [
        "Tester summary:",
        f"- Workspace: {workspace}",
        "- Suggested validation commands:",
    ]

    if commands:
        summary_lines.extend(f"  - {command}" for command in commands)
    else:
        summary_lines.append(
            "  - No obvious project-specific test command detected. Use targeted Python syntax/import checks if applicable."
        )

    summary_lines.append("- Role instruction:")
    summary_lines.append(TESTER_PROMPT.strip())

    summary = "\n".join(summary_lines)
    task_state.add_agent_result("tester", summary)
    return summary


def suggest_commands(workspace: Path) -> list[str]:
    commands: list[str] = []

    if (workspace / "src").exists():
        commands.append("python -m compileall src")

    if (workspace / "scripts" / "evaluate.py").exists():
        commands.append("python scripts/evaluate.py")

    if (workspace / "scripts" / "predict_match.py").exists():
        commands.append(
            "python scripts/predict_match.py --team-a Argentina --team-b France"
        )

    if (workspace / "pytest.ini").exists() or (workspace / "tests").exists():
        commands.append("python -m pytest")

    if (workspace / "package.json").exists():
        commands.append("npm test")

    return commands
