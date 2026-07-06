import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from coding_agent.runtime.cli import CodingAgentCLI
from coding_agent.runtime.orchestrator_settings import OrchestratorSettings


class FakeIO:
    def __init__(self, answers):
        self.answers = list(answers)
        self.messages = []
        self.prompts = []

    def write(self, message=""):
        self.messages.append(message)

    def ask(self, prompt):
        self.prompts.append(prompt)
        return self.answers.pop(0)


class FakeOrchestrator:
    def __init__(self, answers):
        self.settings = OrchestratorSettings()
        self.io = FakeIO(answers)
        self.turn = 0
        self.total_iterations = 0
        self.tasks = []

    def handle_command(self, user_input):
        if user_input == self.settings.exit_command:
            self.io.write(
                f"\nFinished. {self.turn} turns, "
                f"{self.total_iterations} total iterations."
            )
            return "exit"

        return None

    def run_turn(self, user_input):
        self.tasks.append(user_input)
        self.turn += 1


class CodingAgentCLITests(unittest.TestCase):
    def test_cli_routes_normal_input_to_orchestrator_turns(self):
        orchestrator = FakeOrchestrator(["hacer algo", "/exit"])

        CodingAgentCLI(orchestrator).run()

        self.assertEqual(orchestrator.tasks, ["hacer algo"])
        self.assertTrue(
            any("Coding agent ready." in message for message in orchestrator.io.messages)
        )


if __name__ == "__main__":
    unittest.main()
