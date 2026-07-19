import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from coding_agent.agents.pipeline import default_pipeline
from coding_agent.agents.router import SubagentRouter
from coding_agent.core.contracts import AgentContext
from coding_agent.core.task_state import TaskState


class AgentPipelineTests(unittest.TestCase):
    def test_router_selects_implementation_agents_without_fixed_pipeline(self):
        route = SubagentRouter().route("refactor del agente con ruteo")

        self.assertEqual(
            route.selected_names,
            ["explorer", "researcher", "implementer", "tester", "reviewer"],
        )
        self.assertEqual(
            route.reason_for("implementer"),
            "the request asks for concrete code changes",
        )

    def test_router_skips_implementation_agents_for_research_only_request(self):
        route = SubagentRouter().route("investiga documentacion sobre arquitectura")

        self.assertEqual(
            route.selected_names,
            ["researcher"],
        )
        self.assertIn("implementer", [entry.name for entry in route.skipped])

    def test_pipeline_passes_scoped_tools_to_each_selected_subagent(self):
        state = TaskState(original_request="arreglar agente")
        context = AgentContext(config={"workspace": "."})
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

    def test_pipeline_skips_tester_when_implementer_makes_no_changes(self):
        state = TaskState(original_request="arreglar agente")
        context = AgentContext(config={"workspace": "."})
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

    def test_router_uses_explorer_only_for_repo_context_question(self):
        route = SubagentRouter().route("explicame la arquitectura del agente")

        self.assertEqual(
            route.selected_names,
            ["explorer", "researcher"],
        )

    def test_reviewer_changes_requested_marks_task_state(self):
        state = TaskState(original_request="revisa diff")
        context = AgentContext(config={"workspace": "."})

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
