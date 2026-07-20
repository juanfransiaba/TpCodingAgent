import json
from types import SimpleNamespace


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


def fake_route_llm(selected, skipped=None):
    return FakeRouterLLM(
        json.dumps(
            {
                "selected": selected,
                "skipped": skipped or [],
            }
        )
    )
