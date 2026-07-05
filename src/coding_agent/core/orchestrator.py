from __future__ import annotations

from pathlib import Path

from coding_agent.agents.main_agent import prepare_task
from coding_agent.core.harness import run_agent_turn
from coding_agent.core.llm_client import MODEL
from coding_agent.core.planner import get_plan
from coding_agent.core.task_state import TaskState
from coding_agent.memory.conversation_memory import ConversationMemory
from coding_agent.memory.execution_memory import ExecutionMemory
from coding_agent.memory.persistent_memory import PersistentMemoryStore
from coding_agent.observability.tracing import TraceRecorder
from coding_agent.prompts.system_prompt import SYSTEM_PROMPT


class CodingAgentOrchestrator:
    """Coordinates one interactive coding-agent session."""

    def __init__(
        self,
        config: dict,
        memory: PersistentMemoryStore | None = None,
        execution_memory: ExecutionMemory | None = None,
    ):
        self.config = config
        self.memory = memory or PersistentMemoryStore(
            config.get("memory", {}).get("path", "memory/project_memory.json")
        )
        self.execution_memory = execution_memory or ExecutionMemory()
        self.conversation = ConversationMemory(
            [{"role": "system", "content": SYSTEM_PROMPT}]
        )
        self.turn = 0
        self.total_iterations = 0
        self.plan_mode = False
        self.supervision = False

    def chat(self) -> None:
        print("Coding agent ready.")
        print("Commands: /plan, /supervision, /exit")
        print("-" * 50)

        while True:
            user_input = input("\nYou: ").strip()

            if not user_input:
                continue

            command_result = self.handle_command(user_input)

            if command_result == "exit":
                break

            if command_result == "handled":
                continue

            self.run_turn(user_input)

    def handle_command(self, user_input: str) -> str | None:
        command = user_input.lower()

        if command == "/exit":
            print(
                f"\nFinished. {self.turn} turns, "
                f"{self.total_iterations} total iterations."
            )
            return "exit"

        if command == "/plan":
            self.plan_mode = not self.plan_mode
            status = "ON" if self.plan_mode else "OFF"
            print(f"Plan mode: {status}")
            return "handled"

        if command == "/supervision":
            self.supervision = not self.supervision
            status = "ON" if self.supervision else "OFF"
            print(f"Supervision: {status}")
            return "handled"

        return None

    def run_turn(self, user_input: str) -> None:
        self.conversation.add("user", user_input)
        task_state = TaskState(original_request=user_input)
        task_state.add_progress("User request received.")
        self.turn += 1

        print(f"\n{'-' * 50}")

        if self.plan_mode and not self.approve_plan(user_input):
            self.conversation.pop()
            self.turn -= 1
            return

        trace = TraceRecorder(task_state=task_state, model=MODEL, config=self.config)
        coordination_message: dict | None = None

        try:
            with trace.trace_task():
                coordination_content = prepare_task(
                    task_state,
                    self.config,
                    memory=self.memory,
                )
                coordination_message = {
                    "role": "system",
                    "content": coordination_content,
                }
                self.conversation.insert_before_last(coordination_message)

                try:
                    trace.record_event(
                        "coordination_brief",
                        metadata={"content": coordination_content},
                    )
                    response, iterations = run_agent_turn(
                        messages=self.conversation.messages,
                        config=self.config,
                        supervision=self.supervision,
                        task_state=task_state,
                        trace=trace,
                    )
                finally:
                    if coordination_message in self.conversation.messages:
                        self.conversation.remove(coordination_message)

                self.total_iterations += iterations
                task_state.mark_completed(response)
                self.execution_memory.record(task_state)
                self.memory.record_task_state(task_state)
                trace.record_final(task_state)
                state_path = task_state.save_json(
                    Path("runs") / "task_states" / f"{task_state.task_id}.json"
                )
                trace_path = trace.save_local_trace()
                trace.flush()
        except Exception as error:
            task_state.mark_blocked(str(error))
            trace.record_error("orchestrator", error)
            trace.record_final(task_state)
            state_path = task_state.save_json(
                Path("runs") / "task_states" / f"{task_state.task_id}.json"
            )
            trace_path = trace.save_local_trace()
            trace.flush()
            self.execution_memory.record(task_state)

            print(f"\nAgent failed: {error}")
            print(f"Task state saved to: {state_path}")
            print(f"Trace saved to: {trace_path}")
            return

        print(f"\nAgent: {response}")
        print(f"Iterations this turn: {iterations}")
        print(f"Task state saved to: {state_path}")
        print(f"Project memory saved to: {self.memory.storage_path}")
        print(f"Trace saved to: {trace_path}")

    def approve_plan(self, user_input: str) -> bool:
        print("Generating plan...")
        plan = get_plan(self.conversation.messages[:-1], user_input)
        print(f"\nPlan:\n{plan}\n")

        approval = input("Approve plan? [s/n]: ").strip().lower()

        if approval not in ("s", "si", "y", "yes"):
            print("Plan rejected. Task cancelled.")
            return False

        print("Plan approved. Executing...\n")
        return True
