import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from coding_agent.core.task_state import TaskState
from coding_agent.runtime.harness import run_agent_turn


class FakeLLMClient:
    model = "fake-model"

    def __init__(self, messages):
        self.messages = list(messages)

    def chat(self, messages, **kwargs):
        content, tool_calls = self.messages.pop(0)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=content,
                        tool_calls=tool_calls,
                    )
                )
            ],
            usage=None,
        )


def make_tool_call(name, arguments):
    return SimpleNamespace(
        id="call_1",
        function=SimpleNamespace(
            name=name,
            arguments=json.dumps(arguments),
        ),
    )


class HarnessTests(unittest.TestCase):
    def test_run_agent_turn_accepts_injected_llm_without_tools(self):
        messages = [{"role": "user", "content": "hola"}]
        task_state = TaskState(original_request="hola")
        llm = FakeLLMClient([("respuesta final", None)])

        response, iterations = run_agent_turn(
            messages=messages,
            config={"workspace": "."},
            task_state=task_state,
            llm_client=llm,
            tools=[],
            tool_functions={},
            verbose=False,
        )

        self.assertEqual(response, "respuesta final")
        self.assertEqual(iterations, 1)
        self.assertEqual(messages[-1]["role"], "assistant")
        self.assertEqual(task_state.agent_results[-1].agent_name, "llm_agent")

    def test_run_agent_turn_records_custom_agent_name(self):
        messages = [{"role": "user", "content": "hola"}]
        task_state = TaskState(original_request="hola")
        llm = FakeLLMClient([("respuesta final", None)])

        run_agent_turn(
            messages=messages,
            config={"workspace": "."},
            task_state=task_state,
            llm_client=llm,
            tools=[],
            tool_functions={},
            verbose=False,
            agent_name="explorer",
        )

        self.assertEqual(task_state.agent_results[-1].agent_name, "explorer")

    def test_run_agent_turn_can_leave_agent_result_to_caller(self):
        messages = [{"role": "user", "content": "hola"}]
        task_state = TaskState(original_request="hola")
        llm = FakeLLMClient([("respuesta final", None)])

        run_agent_turn(
            messages=messages,
            config={"workspace": "."},
            task_state=task_state,
            llm_client=llm,
            tools=[],
            tool_functions={},
            verbose=False,
            agent_name="explorer",
            record_agent_result=False,
        )

        self.assertEqual(task_state.agent_results, [])

    def test_run_agent_turn_executes_injected_tool_function(self):
        messages = [{"role": "user", "content": "usa echo"}]
        task_state = TaskState(original_request="usa echo")
        llm = FakeLLMClient(
            [
                ("", [make_tool_call("echo", {"text": "hola"})]),
                ("tool usado", None),
            ]
        )

        def echo(text):
            return f"echo:{text}"

        response, iterations = run_agent_turn(
            messages=messages,
            config={"workspace": "."},
            task_state=task_state,
            llm_client=llm,
            tools=[],
            tool_functions={"echo": echo},
            verbose=False,
        )

        self.assertEqual(response, "tool usado")
        self.assertEqual(iterations, 2)
        self.assertEqual(task_state.tool_calls[0].tool_name, "echo")
        self.assertEqual(task_state.tool_calls[0].result_preview, "echo:hola")
        self.assertTrue(
            any(message.get("role") == "tool" for message in messages)
        )

    def test_run_agent_turn_blocks_web_search_before_rag(self):
        messages = [{"role": "user", "content": "busca web"}]
        task_state = TaskState(original_request="busca web")
        llm = FakeLLMClient(
            [
                ("", [make_tool_call("web_search", {"query": "pytest"})]),
                ("primero necesito RAG", None),
            ]
        )
        calls = []

        def web_search(query):
            calls.append(query)
            return "web result"

        response, iterations = run_agent_turn(
            messages=messages,
            config={"workspace": "."},
            task_state=task_state,
            llm_client=llm,
            tools=[],
            tool_functions={"web_search": web_search},
            verbose=False,
            agent_name="researcher",
        )

        self.assertEqual(response, "primero necesito RAG")
        self.assertEqual(iterations, 2)
        self.assertEqual(calls, [])
        self.assertFalse(task_state.tool_calls[0].allowed)
        self.assertIn("RAG-first policy", task_state.tool_calls[0].result_preview)

    def test_run_agent_turn_allows_web_search_after_rag_attempt(self):
        messages = [{"role": "user", "content": "busca docs"}]
        task_state = TaskState(original_request="busca docs")
        llm = FakeLLMClient(
            [
                ("", [make_tool_call("search_rag", {"query": "pytest"})]),
                ("", [make_tool_call("web_search", {"query": "pytest"})]),
                ("respuesta con evidencia", None),
            ]
        )
        calls = []

        def search_rag(query):
            calls.append(("search_rag", query))
            return "No RAG results found."

        def web_search(query):
            calls.append(("web_search", query))
            return "Results:\n  https://example.com/pytest\n"

        response, iterations = run_agent_turn(
            messages=messages,
            config={"workspace": "."},
            task_state=task_state,
            llm_client=llm,
            tools=[],
            tool_functions={
                "search_rag": search_rag,
                "web_search": web_search,
            },
            verbose=False,
            agent_name="researcher",
        )

        self.assertEqual(response, "respuesta con evidencia")
        self.assertEqual(iterations, 3)
        self.assertEqual(
            calls,
            [("search_rag", "pytest"), ("web_search", "pytest")],
        )
        self.assertTrue(task_state.tool_calls[0].allowed)
        self.assertTrue(task_state.tool_calls[1].allowed)

    def test_run_agent_turn_stops_at_max_iterations(self):
        messages = [{"role": "user", "content": "usa echo"}]
        task_state = TaskState(original_request="usa echo")
        llm = FakeLLMClient(
            [
                ("", [make_tool_call("echo", {"text": "hola"})]),
            ]
        )

        def echo(text):
            return f"echo:{text}"

        response, iterations = run_agent_turn(
            messages=messages,
            config={"workspace": "."},
            task_state=task_state,
            llm_client=llm,
            tools=[],
            tool_functions={"echo": echo},
            verbose=False,
            max_iterations=1,
        )

        self.assertEqual(iterations, 1)
        self.assertIn("max_iterations=1", response)
        self.assertEqual(task_state.status, "blocked")
        self.assertEqual(task_state.agent_results[-1].status, "blocked")


if __name__ == "__main__":
    unittest.main()
