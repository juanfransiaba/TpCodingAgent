from coding_agent.llm.client import default_llm_client


def get_plan(messages: list[dict], task: str) -> str:
    """Asks the LLM to plan without executing tools."""

    return default_llm_client.plan(messages, task)
