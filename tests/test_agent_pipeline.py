import contextlib
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from coding_agent.agents.pipeline import default_pipeline
from coding_agent.core.contracts import AgentContext
from coding_agent.core.task_state import TaskState


class FakeRouterLLM:
    model = "fake-router-model"

    def __init__(self, content):
        self.content = content

    def chat(self, messages, **kwargs):
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=self.content),
                )
            ],
            usage=None,
        )


class FakeTrace:
    def __init__(self):
        self.active_subagents = []
        self.started = []
        self.finished = []

    @contextlib.contextmanager
    def trace_subagent(self, agent_name, metadata=None):
        self.started.append((agent_name, metadata or {}))
        self.active_subagents.append(agent_name)
        try:
            yield self
        finally:
            self.finished.append(self.active_subagents.pop())


def fake_route_llm(selected, skipped=None):
    return FakeRouterLLM(
        json.dumps(
            {
                "selected": selected,
                "skipped": skipped or [],
            }
        )
    )


IMPLEMENTATION_ROUTE = [
    {
        "name": "explorer",
        "reason": "the request needs repository context or implementation evidence",
    },
    {
        "name": "implementer",
        "reason": "the request asks for concrete code changes",
    },
    {
        "name": "tester",
        "reason": "implementation work should be validated after writes",
    },
    {
        "name": "reviewer",
        "reason": "implementation work should be reviewed against the request",
    },
]


class AgentPipelineTests(unittest.TestCase):
    def test_pipeline_passes_scoped_tools_to_each_selected_subagent(self):
        state = TaskState(original_request="arreglar agente")
        context = AgentContext(
            config={"workspace": "."},
            llm=fake_route_llm(IMPLEMENTATION_ROUTE),
        )
        calls = []

        def fake_run_agent_turn(**kwargs):
            self.assertFalse(kwargs["record_agent_result"])

            if kwargs["agent_name"] == "implementer":
                kwargs["task_state"].add_tool_call(
                    "write_file",
                    {"path": "agent.py"},
                    True,
                    "File written successfully: agent.py",
                    1,
                )

            tools = [
                tool["function"]["name"]
                for tool in kwargs["tools"]
            ]
            calls.append((kwargs["agent_name"], tools))
            return json.dumps(
                {
                    "status": "completed",
                    "summary": f"{kwargs['agent_name']} completed",
                    "evidence": [f"{kwargs['agent_name']} evidence"],
                    "files_changed": [],
                    "blockers": [],
                    "recommendation": (
                        "approved"
                        if kwargs["agent_name"] == "reviewer"
                        else "continue"
                    ),
                }
            ), 1

        summaries = default_pipeline(run_agent_turn_fn=fake_run_agent_turn).run(
            state,
            context,
        )

        self.assertEqual(
            calls,
            [
                (
                    "explorer",
                    [
                        "read_file",
                        "list_files",
                        "search_rag",
                        "read_project_memory",
                    ],
                ),
                (
                    "implementer",
                    [
                        "read_file",
                        "write_file",
                        "list_files",
                    ],
                ),
                (
                    "tester",
                    [
                        "read_file",
                        "run_command",
                    ],
                ),
                (
                    "reviewer",
                    [
                        "read_file",
                        "run_command",
                    ],
                ),
            ],
        )
        self.assertEqual(
            [result.agent_name for result in state.agent_results],
            ["explorer", "implementer", "tester", "reviewer"],
        )
        self.assertEqual(state.agent_results[0].evidence, ["explorer evidence"])
        self.assertEqual(state.agent_results[-1].recommendation, "approved")
        self.assertEqual(len(summaries), 4)
        self.assertTrue(
            all("Tools allowed:" in summary for summary in summaries)
        )

    def test_pipeline_wraps_each_selected_subagent_in_trace_context(self):
        state = TaskState(original_request="arreglar agente")
        context = AgentContext(
            config={"workspace": "."},
            llm=fake_route_llm(IMPLEMENTATION_ROUTE),
        )
        trace = FakeTrace()
        active_contexts = []

        def fake_run_agent_turn(**kwargs):
            agent_name = kwargs["agent_name"]
            active_contexts.append((agent_name, list(trace.active_subagents)))

            if agent_name == "implementer":
                kwargs["task_state"].add_tool_call(
                    "write_file",
                    {"path": "agent.py"},
                    True,
                    "File written successfully: agent.py",
                    1,
                    agent_name=agent_name,
                )

            return json.dumps(
                {
                    "status": "completed",
                    "summary": f"{agent_name} completed",
                    "evidence": [],
                    "files_changed": [],
                    "blockers": [],
                    "recommendation": (
                        "approved"
                        if agent_name == "reviewer"
                        else "continue"
                    ),
                }
            ), 1

        default_pipeline(
            run_agent_turn_fn=fake_run_agent_turn,
            trace=trace,
        ).run(state, context)

        expected_agents = ["explorer", "implementer", "tester", "reviewer"]

        self.assertEqual(
            [agent_name for agent_name, _ in trace.started],
            expected_agents,
        )
        self.assertEqual(trace.finished, expected_agents)
        self.assertEqual(
            active_contexts,
            [(agent_name, [agent_name]) for agent_name in expected_agents],
        )
        self.assertEqual(
            trace.started[0][1]["route_reason"],
            "the request needs repository context or implementation evidence",
        )
        self.assertEqual(
            trace.started[1][1]["allowed_tools"],
            ["read_file", "write_file", "list_files"],
        )

    def test_pipeline_skips_tester_when_implementer_makes_no_changes(self):
        state = TaskState(original_request="arreglar agente")
        context = AgentContext(
            config={"workspace": "."},
            llm=fake_route_llm(IMPLEMENTATION_ROUTE),
        )
        calls = []

        def fake_run_agent_turn(**kwargs):
            calls.append(kwargs["agent_name"])
            return json.dumps(
                {
                    "status": "completed",
                    "summary": f"{kwargs['agent_name']} completed",
                    "evidence": [],
                    "files_changed": [],
                    "blockers": [],
                    "recommendation": (
                        "approved"
                        if kwargs["agent_name"] == "reviewer"
                        else "continue"
                    ),
                }
            ), 1

        summaries = default_pipeline(run_agent_turn_fn=fake_run_agent_turn).run(
            state,
            context,
        )

        self.assertEqual(calls, ["explorer", "implementer", "reviewer"])
        self.assertEqual(
            [result.agent_name for result in state.agent_results],
            ["explorer", "implementer", "tester", "reviewer"],
        )
        self.assertEqual(state.agent_results[2].status, "skipped")
        self.assertTrue(
            any("tester subagent skipped" in item for item in summaries)
        )
        self.assertTrue(
            any("tester subagent skipped" in item for item in state.observations)
        )

    def test_reviewer_changes_requested_marks_task_state(self):
        state = TaskState(original_request="revisa diff")
        context = AgentContext(
            config={"workspace": "."},
            llm=fake_route_llm(
                [
                    {
                        "name": "reviewer",
                        "reason": "the request asks for review or diff analysis",
                    }
                ]
            ),
        )

        def fake_run_agent_turn(**kwargs):
            recommendation = (
                "changes_requested"
                if kwargs["agent_name"] == "reviewer"
                else "continue"
            )
            blockers = (
                ["missing validation"]
                if kwargs["agent_name"] == "reviewer"
                else []
            )
            return json.dumps(
                {
                    "status": "completed",
                    "summary": f"{kwargs['agent_name']} completed",
                    "evidence": [],
                    "files_changed": [],
                    "blockers": blockers,
                    "recommendation": recommendation,
                }
            ), 1

        default_pipeline(run_agent_turn_fn=fake_run_agent_turn).run(state, context)

        self.assertEqual(state.status, "changes_requested")
        self.assertEqual(state.agent_results[-1].agent_name, "reviewer")
        self.assertEqual(state.agent_results[-1].recommendation, "changes_requested")
        self.assertTrue(
            any(
                "reviewer decision: changes_requested" in item
                for item in state.observations
            )
        )


if __name__ == "__main__":
    unittest.main()
