from coding_agent.core.llm_client import default_llm_client


def get_plan(messages: list[dict], task: str) -> str:
    """Asks the LLM to plan without executing tools."""

    plan_messages = messages + [
        {
            "role": "user",
            "content": (
                f"Task: {task}\n\n"
                "Before doing anything, describe step by step what you will do. "
                "Mention which tools you would use in each step. "
                "Do not execute anything yet."
            ),
        }
    ]

    response = default_llm_client.chat(messages=plan_messages)
    return response.choices[0].message.content
