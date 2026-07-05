from __future__ import annotations


class ConversationMemory:
    """In-memory conversation history for one interactive session."""

    def __init__(self, initial_messages: list[dict] | None = None):
        self.messages = list(initial_messages or [])

    def add(self, role: str, content: str, **extra: object) -> None:
        message = {
            "role": role,
            "content": content,
        }
        message.update(extra)
        self.messages.append(message)

    def insert_before_last(self, message: dict) -> None:
        self.messages.insert(len(self.messages) - 1, message)

    def remove(self, message: dict) -> None:
        self.messages.remove(message)

    def snapshot(self) -> list[dict]:
        return list(self.messages)

    def pop(self) -> dict:
        return self.messages.pop()
