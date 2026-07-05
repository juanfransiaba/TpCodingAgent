from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from coding_agent.agents.main_agent import prepare_task
from coding_agent.core.task_state import TaskState
from coding_agent.llm.client import MODEL
from coding_agent.llm.planner import get_plan
from coding_agent.memory.conversation_memory import ConversationMemory
from coding_agent.memory.execution_memory import ExecutionMemory
from coding_agent.memory.persistent_memory import PersistentMemoryStore
from coding_agent.observability.tracing import TraceRecorder
from coding_agent.runtime.harness import run_agent_turn
from coding_agent.runtime.io import ConsoleIO, UserIO
from coding_agent.runtime.orchestrator_settings import OrchestratorSettings
from coding_agent.security.approval import is_approved


class CodingAgentOrchestrator:

    def __init__(
        self,
        config: dict,
        memory: PersistentMemoryStore | None = None,
        execution_memory: ExecutionMemory | None = None,
        settings: OrchestratorSettings | None = None,
        prepare_task_fn: Callable[..., str] = prepare_task,
        run_agent_turn_fn: Callable[..., tuple[str, int]] = run_agent_turn,
        plan_fn: Callable[[list[dict], str], str] = get_plan,
        trace_factory: Callable[..., TraceRecorder] = TraceRecorder,
        io: UserIO | None = None,
    ):
        self.config = config
        self.settings = settings or OrchestratorSettings.from_config(config)
        self.memory = memory or PersistentMemoryStore(self.settings.memory_path)
        self.execution_memory = execution_memory or ExecutionMemory()
        self.conversation = ConversationMemory(
            [{"role": "system", "content": self.settings.system_prompt}]
        )
        self.prepare_task = prepare_task_fn
        self.run_agent_turn = run_agent_turn_fn
        self.plan = plan_fn
        self.trace_factory = trace_factory
        self.io = io or ConsoleIO()
        self.turn = 0
        self.total_iterations = 0
        self.plan_mode = False
        self.supervision = False

    def chat(self) -> None:
        self.io.write("Coding agent ready.")
        self.io.write(
            "Commands: "
            f"{self.settings.plan_command}, "
            f"{self.settings.supervision_command}, "
            f"{self.settings.exit_command}"
        )
        self.io.write("-" * 50)

        while True:
            user_input = self.io.ask("\nYou: ").strip()

            if not user_input:
                continue

            command_result = self.handle_command(user_input)

            if command_result == "exit":
                break

            if command_result == "handled":
                continue

            self.run_turn(user_input)

    def handle_command(self, user_input: str) -> str | None:
        command = user_input.strip().lower()

        if command == self.settings.exit_command:
            self.io.write(
                f"\nFinished. {self.turn} turns, "
                f"{self.total_iterations} total iterations."
            )
            return "exit"

        if command == self.settings.plan_command:
            self.plan_mode = not self.plan_mode
            status = "ON" if self.plan_mode else "OFF"
            self.io.write(f"Plan mode: {status}")
            return "handled"

        if command == self.settings.supervision_command:
            self.supervision = not self.supervision
            status = "ON" if self.supervision else "OFF"
            self.io.write(f"Supervision: {status}")
            return "handled"

        return None

    def run_turn(self, user_input: str) -> None:
        self.conversation.add("user", user_input)
        task_state = TaskState(original_request=user_input)
        task_state.add_progress("User request received.")
        self.turn += 1

        self.io.write(f"\n{'-' * 50}")

        if self.plan_mode and not self.approve_plan(user_input):
            self.conversation.pop()
            self.turn -= 1
            return

        trace = self.trace_factory(
            task_state=task_state,
            model=MODEL,
            config=self.config,
        )
        coordination_message: dict | None = None

        try:
            with trace.trace_task():
                coordination_content = self.prepare_task(
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
                    response, iterations = self.run_agent_turn(
                        messages=self.conversation.messages,
                        config=self.config,
                        supervision=self.supervision,
                        task_state=task_state,
                        trace=trace,
                        max_iterations=self.settings.max_iterations,
                    )
                finally:
                    if coordination_message in self.conversation.messages:
                        self.conversation.remove(coordination_message)

                self.total_iterations += iterations
                if task_state.status != "blocked":
                    task_state.mark_completed(response)
                self.execution_memory.record(task_state)
                self.memory.record_task_state(task_state)
                trace.record_final(task_state)
                state_path = task_state.save_json(
                    Path(self.settings.task_states_path)
                    / f"{task_state.task_id}.json"
                )
                trace_path = trace.save_local_trace()
                trace.flush()
        except Exception as error:
            task_state.mark_blocked(str(error))
            trace.record_error("orchestrator", error)
            trace.record_final(task_state)
            state_path = task_state.save_json(
                Path(self.settings.task_states_path) / f"{task_state.task_id}.json"
            )
            trace_path = trace.save_local_trace()
            trace.flush()
            self.execution_memory.record(task_state)

            self.io.write(f"\nAgent failed: {error}")
            self.io.write(f"Task state saved to: {state_path}")
            self.io.write(f"Trace saved to: {trace_path}")

            if self.settings.raise_on_error:
                raise

            return

        self.io.write(f"\nAgent: {response}")
        self.io.write(f"Iterations this turn: {iterations}")
        self.io.write(f"Task state saved to: {state_path}")
        self.io.write(f"Project memory saved to: {self.memory.storage_path}")
        self.io.write(f"Trace saved to: {trace_path}")

    def approve_plan(self, user_input: str) -> bool:
        self.io.write("Generating plan...")
        plan = self.plan(self.conversation.messages[:-1], user_input)
        self.io.write(f"\nPlan:\n{plan}\n")

        approval = self.io.ask("Approve plan? [s/n]: ")

        if not is_approved(approval):
            self.io.write("Plan rejected. Task cancelled.")
            return False

        self.io.write("Plan approved. Executing...\n")
        return True
