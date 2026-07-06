import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from coding_agent.agents.planner_agent import PlannerAgent
from coding_agent.agents.pipeline import default_pipeline
from coding_agent.core.contracts import AgentContext
from coding_agent.core.task_state import TaskState


class AgentPipelineTests(unittest.TestCase):
    def test_default_pipeline_records_expected_agents(self):
        state = TaskState(original_request="mejorar arquitectura del agente")
        context = AgentContext(config={"workspace": "."})

        summaries = default_pipeline().run(state, context)

        self.assertEqual(len(summaries), 4)
        self.assertEqual(
            [result.agent_name for result in state.agent_results],
            ["planner", "coder", "test", "reviewer"],
        )
        self.assertTrue(
            all(result.status == "completed" for result in state.agent_results)
        )
        self.assertTrue(all(summary for summary in summaries))

    def test_planner_classifies_request_instead_of_repeating_fixed_flow(self):
        state = TaskState(original_request="explicame la arquitectura del agente")
        context = AgentContext(config={"workspace": "cases/football_predictor"})

        result = PlannerAgent().run(state, context)

        self.assertIn("Task type: analysis", result.summary)
        self.assertIn("Answer without writing files", result.summary)


if __name__ == "__main__":
    unittest.main()
