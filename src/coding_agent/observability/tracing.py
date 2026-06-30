from __future__ import annotations

import json
import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from coding_agent.core.task_state import TaskState, utc_now_iso

load_dotenv()

MAX_PROMPT_CHARS = 12_000
MAX_OUTPUT_CHARS = 4_000


class TraceRecorder:
    """Records local traces and optionally exports them to Langfuse."""

    def __init__(
        self,
        task_state: TaskState,
        model: str,
        config: dict,
    ):
        self.task_state = task_state
        self.model = model
        self.config = config
        self.events: list[dict[str, Any]] = []
        self.started_at = time.perf_counter()
        self.trace_started_at = utc_now_iso()
        self.final_output = ""
        self.langfuse = self._build_langfuse_client()
        self.langfuse_status = "enabled" if self.langfuse else "disabled"

    @contextmanager
    def trace_task(self):
        if not self.langfuse:
            yield self
            return

        try:
            with self.langfuse.start_as_current_observation(
                as_type="span",
                name="coding-agent-task",
            ) as span:
                span.update(
                    input=self.task_state.original_request,
                    metadata={
                        "task_id": self.task_state.task_id,
                        "model": self.model,
                        "workspace": self.config.get("workspace"),
                    },
                )
                yield self
                span.update(
                    output=truncate(self.final_output, MAX_OUTPUT_CHARS),
                    metadata=self.summary_metadata(),
                )
        except Exception as error:
            self.record_error("langfuse_trace_task", error)
            yield self

    def record_event(
        self,
        name: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.events.append(
            {
                "type": "event",
                "name": name,
                "timestamp": utc_now_iso(),
                "metadata": metadata or {},
            }
        )

    def record_llm_call(
        self,
        iteration: int,
        messages: list[dict],
        model: str,
        output: str,
        latency_seconds: float,
        usage: Any = None,
        error: str | None = None,
    ) -> None:
        usage_details = extract_usage(usage)
        estimated_cost = estimate_cost(
            model=model,
            usage_details=usage_details,
            config=self.config,
        )
        payload = {
            "type": "llm_call",
            "timestamp": utc_now_iso(),
            "iteration": iteration,
            "model": model,
            "input": truncate(json_safe(messages), MAX_PROMPT_CHARS),
            "output": truncate(output, MAX_OUTPUT_CHARS),
            "latency_seconds": round(latency_seconds, 4),
            "usage": usage_details,
            "estimated_cost_usd": estimated_cost,
            "error": error,
        }
        self.events.append(payload)

        if not self.langfuse:
            return

        try:
            with self.langfuse.start_as_current_observation(
                as_type="generation",
                name=f"llm-iteration-{iteration}",
                model=model,
            ) as generation:
                generation.update(
                    input=payload["input"],
                    output=payload["output"],
                    metadata={
                        "iteration": iteration,
                        "latency_seconds": payload["latency_seconds"],
                        "estimated_cost_usd": estimated_cost,
                        "error": error,
                    },
                    usage_details=usage_details or None,
                )
        except Exception as langfuse_error:
            self.record_error("langfuse_llm_call", langfuse_error)

    def record_tool_call(
        self,
        tool_name: str,
        args: dict[str, Any],
        allowed: bool,
        result: str,
        iteration: int,
        latency_seconds: float,
    ) -> None:
        metadata = {
            "tool_name": tool_name,
            "args": args,
            "allowed": allowed,
            "iteration": iteration,
            "latency_seconds": round(latency_seconds, 4),
            "sources": extract_sources_from_tool_result(tool_name, result),
        }
        payload = {
            "type": "tool_call",
            "timestamp": utc_now_iso(),
            "metadata": metadata,
            "result_preview": truncate(result, MAX_OUTPUT_CHARS),
        }
        self.events.append(payload)

        if not self.langfuse:
            return

        try:
            with self.langfuse.start_as_current_observation(
                as_type="span",
                name=f"tool-{tool_name}",
            ) as span:
                span.update(
                    input=json_safe(args),
                    output=payload["result_preview"],
                    metadata=metadata,
                )
        except Exception as langfuse_error:
            self.record_error("langfuse_tool_call", langfuse_error)

    def record_final(self, task_state: TaskState) -> None:
        self.final_output = task_state.final_response
        self.events.append(
            {
                "type": "final_result",
                "timestamp": utc_now_iso(),
                "metadata": self.summary_metadata(),
                "output": truncate(task_state.final_response, MAX_OUTPUT_CHARS),
            }
        )

    def record_error(self, name: str, error: Exception | str) -> None:
        self.events.append(
            {
                "type": "error",
                "name": name,
                "timestamp": utc_now_iso(),
                "error": sanitize(str(error)),
            }
        )

    def save_local_trace(self) -> Path:
        local_path = Path(
            self.config.get("observability", {}).get(
                "local_traces_path",
                "runs/traces",
            )
        )
        local_path.mkdir(parents=True, exist_ok=True)
        trace_path = local_path / f"{self.task_state.task_id}.json"

        with trace_path.open("w", encoding="utf-8") as file:
            json.dump(self.to_dict(), file, indent=2, ensure_ascii=True)

        return trace_path

    def flush(self) -> None:
        if not self.langfuse:
            return

        try:
            self.langfuse.flush()
        except Exception as error:
            self.record_error("langfuse_flush", error)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_state.task_id,
            "request": self.task_state.original_request,
            "model": self.model,
            "provider": self.config.get("observability", {}).get("provider"),
            "langfuse_status": self.langfuse_status,
            "started_at": self.trace_started_at,
            "duration_seconds": round(time.perf_counter() - self.started_at, 4),
            "events": self.events,
            "task_state": self.task_state.to_dict(),
        }

    def summary_metadata(self) -> dict[str, Any]:
        usage = aggregate_usage(self.events)
        return {
            "task_id": self.task_state.task_id,
            "iterations": self.task_state.iterations,
            "tool_calls": len(self.task_state.tool_calls),
            "sources": [source.location for source in self.task_state.sources],
            "files_modified": self.task_state.files_modified,
            "errors": self.task_state.errors,
            "usage": usage,
            "estimated_cost_usd": aggregate_cost(self.events),
            "duration_seconds": round(time.perf_counter() - self.started_at, 4),
        }

    def _build_langfuse_client(self):
        if self.config.get("observability", {}).get("provider") != "langfuse":
            return None

        if not os.getenv("LANGFUSE_PUBLIC_KEY") or not os.getenv("LANGFUSE_SECRET_KEY"):
            return None

        try:
            from langfuse import get_client

            client = get_client()
            return client
        except Exception as error:
            self.events.append(
                {
                    "type": "error",
                    "name": "langfuse_init",
                    "timestamp": utc_now_iso(),
                    "error": sanitize(str(error)),
                }
            )
            return None


def extract_usage(usage: Any) -> dict[str, int]:
    if not usage:
        return {}

    if isinstance(usage, dict):
        prompt_tokens = usage.get("prompt_tokens") or usage.get("input_tokens")
        completion_tokens = usage.get("completion_tokens") or usage.get("output_tokens")
        total_tokens = usage.get("total_tokens")
    else:
        prompt_tokens = getattr(usage, "prompt_tokens", None)
        completion_tokens = getattr(usage, "completion_tokens", None)
        total_tokens = getattr(usage, "total_tokens", None)

    return {
        key: value
        for key, value in {
            "input_tokens": prompt_tokens,
            "output_tokens": completion_tokens,
            "total_tokens": total_tokens,
        }.items()
        if value is not None
    }


def estimate_cost(
    model: str,
    usage_details: dict[str, int],
    config: dict,
) -> float | None:
    pricing = config.get("observability", {}).get("pricing", {}).get(model, {})
    input_price = pricing.get("input_per_1m_tokens")
    output_price = pricing.get("output_per_1m_tokens")

    if input_price is None or output_price is None:
        return None

    input_tokens = usage_details.get("input_tokens", 0)
    output_tokens = usage_details.get("output_tokens", 0)

    return round(
        (input_tokens / 1_000_000) * float(input_price)
        + (output_tokens / 1_000_000) * float(output_price),
        8,
    )


def aggregate_usage(events: list[dict[str, Any]]) -> dict[str, int]:
    totals = {
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
    }

    for event in events:
        if event.get("type") != "llm_call":
            continue

        for key in totals:
            totals[key] += event.get("usage", {}).get(key, 0)

    return totals


def aggregate_cost(events: list[dict[str, Any]]) -> float | None:
    costs = [
        event.get("estimated_cost_usd")
        for event in events
        if event.get("type") == "llm_call"
        and event.get("estimated_cost_usd") is not None
    ]

    if not costs:
        return None

    return round(sum(costs), 8)


def extract_sources_from_tool_result(tool_name: str, result: str) -> list[str]:
    if tool_name == "rag_search":
        return [
            line.removeprefix("Fuente:").strip()
            for line in result.splitlines()
            if line.startswith("Fuente:")
        ]

    if tool_name == "web_search":
        return [
            line.strip()
            for line in result.splitlines()
            if line.strip().startswith("http")
        ]

    return []


def truncate(value: Any, limit: int) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=True)

    if len(text) <= limit:
        return text

    return text[:limit] + "\n...[truncated]"


def json_safe(value: Any) -> Any:
    try:
        json.dumps(value)
        return value
    except TypeError:
        return str(value)


def sanitize(text: str) -> str:
    for env_name in (
        "OPENAI_API_KEY",
        "TAVILY_API_KEY",
        "LANGFUSE_SECRET_KEY",
        "LANGFUSE_PUBLIC_KEY",
    ):
        value = os.getenv(env_name)

        if value:
            text = text.replace(value, f"{env_name}=***")

    return text
