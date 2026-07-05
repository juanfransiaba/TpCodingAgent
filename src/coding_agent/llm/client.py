import os
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

MODEL = os.getenv("MODEL", "gpt-5-nano")

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
)


class OpenAILLMClient:
    """Adapter around the OpenAI Chat Completions API."""

    def __init__(
        self,
        model: str = MODEL,
        openai_client: OpenAI | None = None,
    ):
        self.model = model
        self.client = openai_client or client

    def chat(self, messages: list[dict], **kwargs) -> Any:
        return self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            **kwargs,
        )

    def plan(self, messages: list[dict], task: str) -> str:
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

        response = self.chat(messages=plan_messages)
        return response.choices[0].message.content


default_llm_client = OpenAILLMClient()
