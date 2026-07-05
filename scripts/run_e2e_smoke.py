from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = REPO_ROOT / "src"
sys.path.insert(0, str(SRC_PATH))
os.chdir(REPO_ROOT)

from coding_agent.core.config import load_config
from coding_agent.core.task_state import TaskState
from coding_agent.llm.client import MODEL, default_llm_client
from coding_agent.memory.persistent_memory import PersistentMemoryStore
from coding_agent.observability.tracing import TraceRecorder
from coding_agent.prompts.system_prompt import SYSTEM_PROMPT
from coding_agent.rag.retriever import rag_search
from coding_agent.tools.memory_tools import memory_context, remember_decision
from coding_agent.tools.repo_tools import tree_files
from coding_agent.tools.web_search_tool import web_search


def main() -> None:
    config = load_config(str(REPO_ROOT / "agent.config.yaml"))
    request = (
        "E2E smoke test: usar RAG, una tool de repo, busqueda web, memoria, "
        "LLM y observabilidad para explicar como evitar data leakage."
    )
    task_state = TaskState(original_request=request)
    task_state.add_progress("E2E smoke test started.")
    memory = PersistentMemoryStore(
        config.get("memory", {}).get("path", "memory/project_memory.json")
    )
    trace = TraceRecorder(task_state=task_state, model=MODEL, config=config)

    response = ""

    with trace.trace_task():
        memory_result = run_tool(
            trace=trace,
            task_state=task_state,
            tool_name="memory_context",
            args={"storage_path": str(memory.storage_path)},
            function=memory_context,
        )
        rag_result = run_tool(
            trace=trace,
            task_state=task_state,
            tool_name="rag_search",
            args={
                "query": "como evitar data leakage con pandas al calcular features temporales",
                "top_k": 2,
            },
            function=rag_search,
        )
        record_rag_sources(task_state, rag_result)

        tree_result = run_tool(
            trace=trace,
            task_state=task_state,
            tool_name="tree_files",
            args={
                "directory": config.get("workspace", "."),
                "max_depth": 2,
            },
            function=tree_files,
        )
        web_result = run_tool(
            trace=trace,
            task_state=task_state,
            tool_name="web_search",
            args={"query": "data leakage temporal features machine learning"},
            function=web_search,
        )

        messages = build_messages(
            memory_result=memory_result,
            rag_result=rag_result,
            tree_result=tree_result,
            web_result=web_result,
        )
        response = call_llm(trace, messages)

        task_state.mark_completed(response)

        memory_result = run_tool(
            trace=trace,
            task_state=task_state,
            tool_name="remember_decision",
            args={
                "topic": "e2e_smoke_test",
                "decision": (
                    "The agent can run a complete smoke test using RAG, repo tools, "
                    "web search, memory, LLM, local traces, and Langfuse export."
                ),
                "rationale": "This provides delivery evidence for the observability requirement.",
                "storage_path": str(memory.storage_path),
            },
            function=remember_decision,
        )
        trace.record_event("memory_update", metadata={"result": memory_result})

        memory.record_task_state(task_state)
        trace.record_final(task_state)

    state_path = task_state.save_json(
        REPO_ROOT / "runs" / "task_states" / f"{task_state.task_id}.json"
    )
    trace_path = trace.save_local_trace()
    trace.flush()

    print("E2E smoke test finished.")
    print(f"Task id: {task_state.task_id}")
    print(f"Langfuse status: {trace.langfuse_status}")
    print(f"Task state: {state_path}")
    print(f"Local trace: {trace_path}")
    print(f"Project memory: {memory.storage_path}")
    print("")
    print("Final response:")
    print(response)


def run_tool(
    trace: TraceRecorder,
    task_state: TaskState,
    tool_name: str,
    args: dict,
    function: Callable,
) -> str:
    started_at = time.perf_counter()

    try:
        result = function(**args)
        allowed = True
    except Exception as error:
        result = f"Tool execution error in {tool_name}: {error}"
        allowed = False
        task_state.add_error(result)
        trace.record_error(tool_name, error)

    latency_seconds = time.perf_counter() - started_at
    result_text = str(result)
    task_state.add_tool_call(
        tool_name=tool_name,
        args=args,
        allowed=allowed,
        result=result_text,
        iteration=1,
    )
    trace.record_tool_call(
        tool_name=tool_name,
        args=args,
        allowed=allowed,
        result=result_text,
        iteration=1,
        latency_seconds=latency_seconds,
    )
    return result_text


def build_messages(
    memory_result: str,
    rag_result: str,
    tree_result: str,
    web_result: str,
) -> list[dict]:
    evidence = "\n\n".join(
        [
            "MEMORY CONTEXT:",
            memory_result[:2_000],
            "RAG RESULTS:",
            rag_result[:4_000],
            "REPOSITORY TREE:",
            tree_result[:2_000],
            "WEB SEARCH:",
            web_result[:2_000],
        ]
    )

    return [
        {"role": "system", "content": SYSTEM_PROMPT.strip()},
        {
            "role": "user",
            "content": (
                "Con esta evidencia, responde en espanol y en no mas de 6 bullets: "
                "que regla debe seguir un caso de prediccion de futbol para evitar "
                "data leakage al calcular features temporales. Distingui RAG, repo, "
                "web y memoria cuando corresponda."
            ),
        },
        {"role": "user", "content": evidence},
    ]


def call_llm(trace: TraceRecorder, messages: list[dict]) -> str:
    started_at = time.perf_counter()

    try:
        response = default_llm_client.chat(messages=messages)
        content = response.choices[0].message.content or ""
        trace.record_llm_call(
            iteration=1,
            messages=messages,
            model=MODEL,
            output=content,
            latency_seconds=time.perf_counter() - started_at,
            usage=getattr(response, "usage", None),
        )
        return content
    except Exception as error:
        trace.record_llm_call(
            iteration=1,
            messages=messages,
            model=MODEL,
            output="",
            latency_seconds=time.perf_counter() - started_at,
            usage=None,
            error=str(error),
        )
        raise


def record_rag_sources(task_state: TaskState, rag_result: str) -> None:
    for line in rag_result.splitlines():
        if not line.startswith("Fuente:"):
            continue

        source = line.removeprefix("Fuente:").strip()
        task_state.add_source(
            kind="rag",
            title=Path(source).name,
            location=source,
            summary="Retrieved during E2E smoke test.",
        )


if __name__ == "__main__":
    main()
