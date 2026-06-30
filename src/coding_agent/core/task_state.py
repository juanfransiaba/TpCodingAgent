from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class SourceRecord:
    kind: str
    title: str
    location: str
    summary: str = ""


@dataclass
class ToolCallRecord:
    tool_name: str
    args: dict[str, Any]
    allowed: bool
    result_preview: str
    iteration: int
    timestamp: str = field(default_factory=utc_now_iso)


@dataclass
class AgentResult:
    agent_name: str
    summary: str
    status: str = "completed"
    timestamp: str = field(default_factory=utc_now_iso)


@dataclass
class TaskState:
    original_request: str
    task_id: str = field(default_factory=lambda: uuid4().hex)
    status: str = "running"
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    current_step: str = ""
    iterations: int = 0
    progress: list[str] = field(default_factory=list)
    agent_results: list[AgentResult] = field(default_factory=list)
    sources: list[SourceRecord] = field(default_factory=list)
    files_modified: list[str] = field(default_factory=list)
    observations: list[str] = field(default_factory=list)
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    final_response: str = ""

    def touch(self) -> None:
        self.updated_at = utc_now_iso()

    def add_progress(self, message: str) -> None:
        self.progress.append(message)
        self.current_step = message
        self.touch()

    def add_agent_result(
        self,
        agent_name: str,
        summary: str,
        status: str = "completed",
    ) -> None:
        self.agent_results.append(
            AgentResult(
                agent_name=agent_name,
                summary=summary,
                status=status,
            )
        )
        self.touch()

    def add_source(
        self,
        kind: str,
        title: str,
        location: str,
        summary: str = "",
    ) -> None:
        self.sources.append(
            SourceRecord(
                kind=kind,
                title=title,
                location=location,
                summary=summary,
            )
        )
        self.touch()

    def add_file_modified(self, path: str) -> None:
        if path not in self.files_modified:
            self.files_modified.append(path)
        self.touch()

    def add_observation(self, observation: str) -> None:
        self.observations.append(observation)
        self.touch()

    def add_error(self, error: str) -> None:
        self.errors.append(error)
        self.touch()

    def add_tool_call(
        self,
        tool_name: str,
        args: dict[str, Any],
        allowed: bool,
        result: str,
        iteration: int,
    ) -> None:
        self.tool_calls.append(
            ToolCallRecord(
                tool_name=tool_name,
                args=args,
                allowed=allowed,
                result_preview=result[:500],
                iteration=iteration,
            )
        )

        if tool_name == "write_file" and allowed and "path" in args:
            self.add_file_modified(str(args["path"]))

        self.touch()

    def set_iterations(self, iterations: int) -> None:
        self.iterations = iterations
        self.touch()

    def mark_completed(self, final_response: str) -> None:
        self.status = "completed"
        self.final_response = final_response
        self.touch()

    def mark_blocked(self, reason: str) -> None:
        self.status = "blocked"
        self.add_error(reason)
        self.touch()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def save_json(self, path: str | Path) -> Path:
        import json

        resolved_path = Path(path)
        resolved_path.parent.mkdir(parents=True, exist_ok=True)

        with resolved_path.open("w", encoding="utf-8") as file:
            json.dump(self.to_dict(), file, indent=2, ensure_ascii=True)

        return resolved_path

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TaskState:
        data = data.copy()
        data["sources"] = [SourceRecord(**source) for source in data.get("sources", [])]
        data["tool_calls"] = [
            ToolCallRecord(**tool_call)
            for tool_call in data.get("tool_calls", [])
        ]
        data["agent_results"] = [
            AgentResult(**agent_result)
            for agent_result in data.get("agent_results", [])
        ]
        return cls(**data)

    @classmethod
    def load_json(cls, path: str | Path) -> TaskState:
        import json

        with Path(path).open("r", encoding="utf-8") as file:
            return cls.from_dict(json.load(file))
