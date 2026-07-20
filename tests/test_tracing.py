import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from coding_agent.core.task_state import TaskState
from coding_agent.observability.tracing import TraceRecorder


class FakeLangfuse:
    def __init__(self):
        self.stack = []
        self.observations = []

    def start_as_current_observation(self, as_type, name, **kwargs):
        return FakeObservation(self, as_type, name, kwargs)


class FakeObservation:
    def __init__(self, client, as_type, name, kwargs):
        self.client = client
        self.as_type = as_type
        self.name = name
        self.kwargs = kwargs
        self.parent = None
        self.updates = []

    def __enter__(self):
        self.parent = self.client.stack[-1].name if self.client.stack else None
        self.client.stack.append(self)
        self.client.observations.append(self)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.client.stack.pop()
        return False

    def update(self, **kwargs):
        self.updates.append(kwargs)


class TraceRecorderTests(unittest.TestCase):
    def test_trace_subagent_records_local_boundaries_and_activity(self):
        state = TaskState(original_request="inspeccionar repo")
        trace = TraceRecorder(
            task_state=state,
            model="fake-model",
            config={"observability": {"provider": "local"}},
        )

        with trace.trace_subagent(
            "explorer",
            metadata={
                "route_reason": "the request needs repository context",
                "allowed_tools": ["list_files"],
            },
        ):
            state.add_tool_call(
                "list_files",
                {"directory": "."},
                True,
                "[DIR] src",
                1,
                agent_name="explorer",
            )
            state.add_agent_result(
                "explorer",
                "repo inspected",
                evidence=["list_files showed src"],
            )

        trace.record_llm_call(
            iteration=1,
            messages=[{"role": "user", "content": "hola"}],
            model="fake-model",
            output="ok",
            latency_seconds=0.01,
            agent_name="explorer",
        )

        started = [
            event
            for event in trace.events
            if event.get("name") == "subagent_started"
        ]
        finished = [
            event
            for event in trace.events
            if event.get("name") == "subagent_finished"
        ]
        llm_calls = [
            event for event in trace.events if event.get("type") == "llm_call"
        ]

        self.assertEqual(started[0]["metadata"]["agent_name"], "explorer")
        self.assertEqual(finished[0]["metadata"]["status"], "completed")
        self.assertEqual(finished[0]["metadata"]["tool_calls"], 1)
        self.assertEqual(llm_calls[0]["agent_name"], "explorer")

    def test_trace_subagent_uses_recorded_agent_result_status(self):
        state = TaskState(original_request="editar repo")
        trace = TraceRecorder(
            task_state=state,
            model="fake-model",
            config={"observability": {"provider": "local"}},
        )

        with trace.trace_subagent("implementer"):
            state.add_error("write failed")
            state.add_agent_result(
                "implementer",
                "implementer subagent failed: write failed",
                status="error",
                blockers=["write failed"],
                recommendation="blocked",
            )

        finished = [
            event
            for event in trace.events
            if event.get("name") == "subagent_finished"
        ]

        self.assertEqual(finished[0]["metadata"]["status"], "error")
        self.assertEqual(finished[0]["metadata"]["errors"], ["write failed"])

    def test_langfuse_observations_nest_under_subagent_span(self):
        state = TaskState(original_request="inspeccionar repo")
        trace = TraceRecorder(
            task_state=state,
            model="fake-model",
            config={"observability": {"provider": "local"}},
        )
        fake_langfuse = FakeLangfuse()
        trace.langfuse = fake_langfuse

        with trace.trace_task():
            with trace.trace_subagent("explorer"):
                trace.record_llm_call(
                    iteration=1,
                    messages=[{"role": "user", "content": "hola"}],
                    model="fake-model",
                    output="ok",
                    latency_seconds=0.01,
                    agent_name="explorer",
                )
                trace.record_tool_call(
                    tool_name="list_files",
                    args={"directory": "."},
                    allowed=True,
                    result="[DIR] src",
                    iteration=1,
                    latency_seconds=0.01,
                    agent_name="explorer",
                )

        observations = {
            observation.name: observation
            for observation in fake_langfuse.observations
        }

        self.assertIsNone(observations["coding-agent-task"].parent)
        self.assertEqual(observations["agent-explorer"].parent, "coding-agent-task")
        self.assertEqual(observations["llm-iteration-1"].parent, "agent-explorer")
        self.assertEqual(observations["tool-list_files"].parent, "agent-explorer")


if __name__ == "__main__":
    unittest.main()
