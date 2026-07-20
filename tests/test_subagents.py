import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from coding_agent.agents.subagents import (
    ImplementerSubagent,
    ReviewerSubagent,
    SubagentRunContext,
    TesterSubagent,
)
from coding_agent.core.contracts import AgentContext
from coding_agent.core.task_state import TaskState


def make_context(
    state,
    run_agent_turn=None,
    implementation_attempted=False,
    successful_writes_before_implementation=0,
):
    return SubagentRunContext(
        state=state,
        agent_context=AgentContext(config={"workspace": "."}),
        previous_summaries=[],
        run_agent_turn=run_agent_turn or (lambda **kwargs: ("{}", 1)),
        trace=None,
        supervision=False,
        verbose=False,
        implementation_attempted=implementation_attempted,
        successful_writes_before_implementation=successful_writes_before_implementation,
    )


class SubagentClassTests(unittest.TestCase):
    def test_implementer_marks_implementation_flow(self):
        self.assertTrue(ImplementerSubagent().marks_implementation_attempted)

    def test_tester_skips_when_implementer_made_no_successful_writes(self):
        state = TaskState(original_request="arreglar agente")
        subagent = TesterSubagent()
        context = make_context(
            state,
            implementation_attempted=True,
            successful_writes_before_implementation=0,
        )

        self.assertTrue(subagent.should_skip(context))

        summary = subagent.skip(context)

        self.assertIn("tester subagent skipped", summary)
        self.assertEqual(state.agent_results[-1].agent_name, "tester")
        self.assertEqual(state.agent_results[-1].status, "skipped")

    def test_reviewer_applies_changes_requested_decision(self):
        state = TaskState(original_request="revisa diff")
        subagent = ReviewerSubagent()

        def fake_run_agent_turn(**kwargs):
            return json.dumps(
                {
                    "status": "completed",
                    "summary": "missing focused test",
                    "evidence": [],
                    "files_changed": [],
                    "blockers": ["missing focused test"],
                    "recommendation": "changes_requested",
                }
            ), 1

        subagent.run(make_context(state, run_agent_turn=fake_run_agent_turn))

        self.assertEqual(state.status, "changes_requested")
        self.assertEqual(
            state.agent_results[-1].recommendation,
            "changes_requested",
        )
        self.assertTrue(
            any(
                "reviewer decision: changes_requested" in observation
                for observation in state.observations
            )
        )


if __name__ == "__main__":
    unittest.main()
