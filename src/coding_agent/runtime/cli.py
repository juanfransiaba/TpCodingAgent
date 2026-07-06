from __future__ import annotations

from coding_agent.runtime.orchestrator import CodingAgentOrchestrator


class CodingAgentCLI:
    """Interactive command-line interface for the coding agent."""

    def __init__(self, orchestrator: CodingAgentOrchestrator):
        self.orchestrator = orchestrator

    def run(self) -> None:
        io = self.orchestrator.io
        settings = self.orchestrator.settings

        io.write("Coding agent ready.")
        io.write(
            "Commands: "
            f"{settings.plan_command}, "
            f"{settings.supervision_command}, "
            f"{settings.exit_command}"
        )
        io.write("-" * 50)

        while True:
            user_input = io.ask("\nYou: ").strip()

            if not user_input:
                continue

            command_result = self.orchestrator.handle_command(user_input)

            if command_result == "exit":
                break

            if command_result == "handled":
                continue

            self.orchestrator.run_turn(user_input)
