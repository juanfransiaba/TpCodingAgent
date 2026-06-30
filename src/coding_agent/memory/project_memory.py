from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from coding_agent.core.task_state import TaskState, utc_now_iso

DEFAULT_MEMORY_PATH = Path("memory") / "project_memory.json"
MAX_CONTEXT_ITEMS = 8


@dataclass
class SemanticMemory:
    topic: str
    decision: str
    rationale: str
    timestamp: str = field(default_factory=utc_now_iso)


@dataclass
class ProceduralMemory:
    command: str
    purpose: str
    last_result: str = ""
    timestamp: str = field(default_factory=utc_now_iso)


@dataclass
class EpisodicMemory:
    task_id: str
    request: str
    summary: str
    files_modified: list[str] = field(default_factory=list)
    sources_used: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=utc_now_iso)


class ProjectMemory:
    """Persistent project memory stored as auditable JSON.

    The memory is intentionally simple:
    - semantic: facts and decisions,
    - procedural: useful commands,
    - episodic: task/session summaries.
    """

    def __init__(self, storage_path: str | Path = DEFAULT_MEMORY_PATH):
        self.storage_path = Path(storage_path)
        self.data = self._load_memory()

    def remember_decision(self, topic: str, decision: str, rationale: str) -> None:
        """Store an architectural or project decision."""

        memory = SemanticMemory(
            topic=topic.strip(),
            decision=decision.strip(),
            rationale=rationale.strip(),
        )
        self.data["semantic"] = upsert_by_key(
            self.data["semantic"],
            asdict(memory),
            key="topic",
        )
        self.save()

    def remember_command(
        self,
        command: str,
        purpose: str,
        last_result: str = "",
    ) -> None:
        """Store a useful command that is safe and relevant for the project."""

        memory = ProceduralMemory(
            command=command.strip(),
            purpose=purpose.strip(),
            last_result=last_result.strip()[:500],
        )
        self.data["procedural"] = upsert_by_key(
            self.data["procedural"],
            asdict(memory),
            key="command",
        )
        self.save()

    def remember_episode(
        self,
        task_id: str,
        request: str,
        summary: str,
        files_modified: list[str] | None = None,
        sources_used: list[str] | None = None,
        errors: list[str] | None = None,
    ) -> None:
        """Store a task milestone or session summary."""

        memory = EpisodicMemory(
            task_id=task_id,
            request=request.strip(),
            summary=summary.strip(),
            files_modified=files_modified or [],
            sources_used=sources_used or [],
            errors=errors or [],
        )
        self.data["episodic"].append(asdict(memory))
        self.data["episodic"] = self.data["episodic"][-MAX_CONTEXT_ITEMS:]
        self.save()

    def record_task_state(self, task_state: TaskState) -> None:
        """Persist useful memory after a task reaches a milestone."""

        summary = build_episode_summary(task_state)
        source_locations = [
            f"{source.kind}:{source.location}"
            for source in task_state.sources
        ]

        self.remember_episode(
            task_id=task_state.task_id,
            request=task_state.original_request,
            summary=summary,
            files_modified=task_state.files_modified,
            sources_used=source_locations,
            errors=task_state.errors,
        )

        for tool_call in task_state.tool_calls:
            if tool_call.tool_name != "run_command" or not tool_call.allowed:
                continue

            command = str(tool_call.args.get("command", "")).strip()

            if not command or "Return code: 0" not in tool_call.result_preview:
                continue

            self.remember_command(
                command=command,
                purpose=f"Worked during task: {task_state.original_request[:120]}",
                last_result=tool_call.result_preview,
            )

    def get_relevant_context(self) -> str:
        """Format memory as compact prompt context."""

        lines = [
            "Persistent project memory:",
            "Semantic memory - facts and decisions:",
        ]

        semantic = self.data.get("semantic", [])[-MAX_CONTEXT_ITEMS:]
        if semantic:
            lines.extend(
                f"- {item['topic']}: {item['decision']} Reason: {item['rationale']}"
                for item in semantic
            )
        else:
            lines.append("- No semantic decisions recorded yet.")

        lines.append("")
        lines.append("Procedural memory - useful commands:")
        procedural = self.data.get("procedural", [])[-MAX_CONTEXT_ITEMS:]
        if procedural:
            lines.extend(
                f"- {item['command']} Purpose: {item['purpose']}"
                for item in procedural
            )
        else:
            lines.append("- No useful commands recorded yet.")

        lines.append("")
        lines.append("Episodic memory - recent task history:")
        episodic = self.data.get("episodic", [])[-MAX_CONTEXT_ITEMS:]
        if episodic:
            lines.extend(
                f"- {item['request']}: {item['summary']}"
                for item in episodic
            )
        else:
            lines.append("- No prior task episodes recorded yet.")

        return "\n".join(lines)

    def save(self) -> Path:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        with self.storage_path.open("w", encoding="utf-8") as file:
            json.dump(self.data, file, indent=2, ensure_ascii=True)

        return self.storage_path

    def _load_memory(self) -> dict[str, list[dict[str, Any]]]:
        if not self.storage_path.exists():
            return empty_memory()

        with self.storage_path.open("r", encoding="utf-8") as file:
            raw_data = json.load(file)

        return {
            "semantic": list(raw_data.get("semantic", [])),
            "procedural": list(raw_data.get("procedural", [])),
            "episodic": list(raw_data.get("episodic", [])),
        }


def build_episode_summary(task_state: TaskState) -> str:
    if task_state.final_response:
        return task_state.final_response[:800]

    if task_state.errors:
        return f"Task ended with errors: {'; '.join(task_state.errors[-3:])}"

    if task_state.progress:
        return "Latest progress: " + task_state.progress[-1]

    return "Task finished without a final response."


def empty_memory() -> dict[str, list[dict[str, Any]]]:
    return {
        "semantic": [],
        "procedural": [],
        "episodic": [],
    }


def upsert_by_key(
    items: list[dict[str, Any]],
    new_item: dict[str, Any],
    key: str,
) -> list[dict[str, Any]]:
    filtered_items = [
        item
        for item in items
        if item.get(key) != new_item.get(key)
    ]
    filtered_items.append(new_item)
    return filtered_items[-MAX_CONTEXT_ITEMS:]
