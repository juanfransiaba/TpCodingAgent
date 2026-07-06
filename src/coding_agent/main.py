from coding_agent.core.config import load_config
from coding_agent.runtime.cli import CodingAgentCLI
from coding_agent.runtime.orchestrator import CodingAgentOrchestrator


def chat() -> None:
    config = load_config()
    orchestrator = CodingAgentOrchestrator(config)
    cli = CodingAgentCLI(orchestrator)
    cli.run()


if __name__ == "__main__":
    chat()
