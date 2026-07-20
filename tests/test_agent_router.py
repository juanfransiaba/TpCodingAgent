import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from coding_agent.agents.router import SubagentRouter
from coding_agent.agents.route_models import RouteClassificationError


class FakeRouterLLM:
    model = "fake-router-model"

    def __init__(self, content):
        self.content = content
        self.calls = []

    def chat(self, messages, **kwargs):
        self.calls.append(messages)
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
        self.llm_calls = []
        self.errors = []

    def record_llm_call(self, **kwargs):
        self.llm_calls.append(kwargs)

    def record_error(self, name, error):
        self.errors.append((name, str(error)))


class SubagentRouterTests(unittest.TestCase):
    def test_router_uses_llm_classification(self):
        llm = FakeRouterLLM(
            json.dumps(
                {
                    "selected": [
                        {
                            "name": "implementer",
                            "reason": "the user wants a concrete code change",
                        }
                    ],
                    "skipped": [],
                }
            )
        )
        trace = FakeTrace()

        route = SubagentRouter().route(
            "mandale mecha a la pantalla principal",
            llm_client=llm,
            trace=trace,
        )

        self.assertEqual(
            route.selected_names,
            ["explorer", "implementer", "tester", "reviewer"],
        )
        self.assertEqual(
            route.reason_for("implementer"),
            "the user wants a concrete code change",
        )
        self.assertEqual(len(llm.calls), 1)
        self.assertEqual(
            trace.llm_calls[0]["observation_name"],
            "router-classification",
        )
        self.assertEqual(trace.llm_calls[0]["agent_name"], "router")

    def test_router_normalizes_llm_output_to_known_agents_and_order(self):
        llm = FakeRouterLLM(
            """
```json
{
  "selected": [
    {"name": "reviewer", "reason": "review requested"},
    {"name": "unknown", "reason": "ignored"},
    {"name": "explorer", "reason": "repo evidence needed"}
  ],
  "skipped": [
    {"name": "implementer", "reason": "no writes requested"}
  ]
}
```
""".strip()
        )

        route = SubagentRouter().route("mirame esto", llm_client=llm)

        self.assertEqual(route.selected_names, ["explorer", "reviewer"])
        self.assertEqual(route.reason_for("explorer"), "repo evidence needed")
        self.assertIn("implementer", [entry.name for entry in route.skipped])

    def test_router_rejects_invalid_llm_output_without_local_route_guessing(self):
        llm = FakeRouterLLM("no json here")
        trace = FakeTrace()

        with self.assertRaises(RouteClassificationError):
            SubagentRouter().route(
                "refactor del agente con ruteo",
                llm_client=llm,
                trace=trace,
            )

        self.assertEqual(trace.errors[0][0], "subagent_router")

    def test_router_requires_llm_client(self):
        with self.assertRaises(RouteClassificationError):
            SubagentRouter().route("refactor del agente con ruteo")


if __name__ == "__main__":
    unittest.main()
