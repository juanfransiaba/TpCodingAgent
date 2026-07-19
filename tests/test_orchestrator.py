import contextlib
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from coding_agent.runtime.orchestrator import CodingAgentOrchestrator
from coding_agent.runtime.orchestrator_settings import OrchestratorSettings


class FakeMemory:
    def __init__(self, storage_path):
        self.storage_path = Path(storage_path)
        self.recorded = []

    def get_relevant_context(self):
        return "fake memory context"

    def record_task_state(self, task_state):
        self.recorded.append(task_state)


class FakeTrace:
    def __init__(self, task_state, model, config):
        self.task_state = task_state
        self.model = model
        self.config = config
        self.events = []

    @contextlib.contextmanager
    def trace_task(self):
        yield self

    def record_event(self, name, metadata=None):
        self.events.append((name, metadata or {}))

    def record_final(self, task_state):
        self.final_task_state = task_state

    def record_error(self, name, error):
        self.events.append((name, {"error": str(error)}))

    def save_local_trace(self):
        return Path("fake-trace.json")

    def flush(self):
        return None


class FakeIO:
    def __init__(self, answers=None):
        self.answers = list(answers or [])
        self.messages = []
        self.prompts = []

    def write(self, message=""):
        self.messages.append(message)

    def ask(self, prompt):
        self.prompts.append(prompt)
        if self.answers:
            return self.answers.pop(0)
        return ""


class OrchestratorTests(unittest.TestCase):
    def test_settings_can_be_loaded_from_config(self):
        settings = OrchestratorSettings.from_config(
            {
                "memory": {"path": "custom/memory.json"},
                "runs": {"task_states_path": "custom/task_states"},
                "orchestrator": {
                    "plan_command": "/p",
                    "supervision_command": "/s",
                    "exit_command": "/q",
                    "raise_on_error": True,
                    "max_iterations": 3,
                },
            }
        )

        self.assertEqual(settings.memory_path, "custom/memory.json")
        self.assertEqual(settings.task_states_path, "custom/task_states")
        self.assertEqual(settings.plan_command, "/p")
        self.assertEqual(settings.supervision_command, "/s")
        self.assertEqual(settings.exit_command, "/q")
        self.assertTrue(settings.raise_on_error)
        self.assertEqual(settings.max_iterations, 3)

    def test_handle_command_uses_configurable_commands(self):
        settings = OrchestratorSettings(
            memory_path="memory.json",
            plan_command="/p",
            supervision_command="/s",
            exit_command="/q",
        )
        orchestrator = CodingAgentOrchestrator(
            config={},
            memory=FakeMemory("memory.json"),
            settings=settings,
            io=FakeIO(),
        )

        plan_result = orchestrator.handle_command("/p")
        supervision_result = orchestrator.handle_command("/s")
        exit_result = orchestrator.handle_command("/q")

        self.assertEqual(plan_result, "handled")
        self.assertEqual(supervision_result, "handled")
        self.assertEqual(exit_result, "exit")
        self.assertTrue(orchestrator.plan_mode)
        self.assertTrue(orchestrator.supervision)

    def test_run_turn_uses_injected_dependencies_and_task_state_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            task_states_path = Path(temp_dir) / "task_states"
            memory = FakeMemory(Path(temp_dir) / "memory.json")
            settings = OrchestratorSettings(
                memory_path=str(memory.storage_path),
                task_states_path=str(task_states_path),
            )

            def fake_prepare_task(task_state, config, memory=None):
                return "coordination brief"

            def fake_run_agent_turn(**kwargs):
                return "final answer", 1

            orchestrator = CodingAgentOrchestrator(
                config={},
                memory=memory,
                settings=settings,
                prepare_task_fn=fake_prepare_task,
                run_agent_turn_fn=fake_run_agent_turn,
                trace_factory=FakeTrace,
                io=FakeIO(),
            )

            orchestrator.run_turn("hacer algo")

            saved_states = list(task_states_path.glob("*.json"))

            self.assertEqual(orchestrator.turn, 1)
            self.assertEqual(orchestrator.total_iterations, 1)
            self.assertEqual(len(memory.recorded), 1)
            self.assertEqual(memory.recorded[0].final_response, "final answer")
            self.assertEqual(len(saved_states), 1)

    def test_plan_mode_executes_after_approval(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            task_states_path = Path(temp_dir) / "task_states"
            memory = FakeMemory(Path(temp_dir) / "memory.json")
            settings = OrchestratorSettings(
                memory_path=str(memory.storage_path),
                task_states_path=str(task_states_path),
            )
            executed = []

            def fake_prepare_task(task_state, config, memory=None):
                return "coordination brief"

            def fake_plan(messages, task):
                return "approved plan"

            def fake_run_agent_turn(**kwargs):
                executed.append(kwargs["messages"][-1]["content"])
                return "final answer", 1

            orchestrator = CodingAgentOrchestrator(
                config={},
                memory=memory,
                settings=settings,
                prepare_task_fn=fake_prepare_task,
                run_agent_turn_fn=fake_run_agent_turn,
                plan_fn=fake_plan,
                trace_factory=FakeTrace,
                io=FakeIO(["sí"]),
            )
            orchestrator.plan_mode = True

            orchestrator.run_turn("hacer algo")

            self.assertEqual(executed, ["hacer algo"])
            self.assertEqual(orchestrator.total_iterations, 1)
            self.assertEqual(memory.recorded[0].final_response, "final answer")

    def test_reviewer_changes_requested_is_not_marked_completed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            task_states_path = Path(temp_dir) / "task_states"
            memory = FakeMemory(Path(temp_dir) / "memory.json")
            settings = OrchestratorSettings(
                memory_path=str(memory.storage_path),
                task_states_path=str(task_states_path),
            )

            def fake_prepare_task(task_state, config, memory=None):
                task_state.add_agent_result(
                    "reviewer",
                    "missing focused tests",
                    blockers=["missing focused tests"],
                    recommendation="changes_requested",
                )
                task_state.mark_changes_requested(
                    "reviewer decision: changes_requested. missing focused tests"
                )
                return "coordination brief"

            def fake_run_agent_turn(**kwargs):
                return "final answer", 1

            orchestrator = CodingAgentOrchestrator(
                config={},
                memory=memory,
                settings=settings,
                prepare_task_fn=fake_prepare_task,
                run_agent_turn_fn=fake_run_agent_turn,
                trace_factory=FakeTrace,
                io=FakeIO(),
            )

            orchestrator.run_turn("revisar")

            self.assertEqual(memory.recorded[0].status, "changes_requested")
            self.assertIn(
                "Reviewer decision: changes_requested",
                memory.recorded[0].final_response,
            )

    def test_run_turn_can_reraise_errors_after_recording(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            task_states_path = Path(temp_dir) / "task_states"
            settings = OrchestratorSettings(
                memory_path=str(Path(temp_dir) / "memory.json"),
                task_states_path=str(task_states_path),
                raise_on_error=True,
            )

            def fake_prepare_task(task_state, config, memory=None):
                return "coordination brief"

            def failing_run_agent_turn(**kwargs):
                raise RuntimeError("boom")

            orchestrator = CodingAgentOrchestrator(
                config={},
                memory=FakeMemory(settings.memory_path),
                settings=settings,
                prepare_task_fn=fake_prepare_task,
                run_agent_turn_fn=failing_run_agent_turn,
                trace_factory=FakeTrace,
                io=FakeIO(),
            )

            with self.assertRaises(RuntimeError):
                orchestrator.run_turn("fallar")

            saved_states = list(task_states_path.glob("*.json"))
            self.assertEqual(len(saved_states), 1)


if __name__ == "__main__":
    unittest.main()
