from coding_agent.core.config import load_config
from coding_agent.core.orchestrator import CodingAgentOrchestrator


def chat() -> None:
    config = load_config()
    orchestrator = CodingAgentOrchestrator(config)
    orchestrator.chat()


if __name__ == "__main__":
    chat()
