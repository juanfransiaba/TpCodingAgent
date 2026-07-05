from coding_agent.memory.project_memory import ProjectMemory


def remember_decision(
    topic: str,
    decision: str,
    rationale: str,
    storage_path: str = "memory/project_memory.json",
) -> str:
    """Store a semantic project decision in persistent memory."""

    if not topic.strip() or not decision.strip():
        return "Error: topic and decision are required."

    memory = ProjectMemory(storage_path)
    memory.remember_decision(topic, decision, rationale)
    return f"Decision remembered: {topic}"


def remember_command(
    command: str,
    purpose: str,
    storage_path: str = "memory/project_memory.json",
) -> str:
    """Store a useful project command in persistent memory."""

    if not command.strip() or not purpose.strip():
        return "Error: command and purpose are required."

    memory = ProjectMemory(storage_path)
    memory.remember_command(command, purpose)
    return f"Command remembered: {command}"


def memory_context(storage_path: str = "memory/project_memory.json") -> str:
    """Return compact persistent memory context."""

    memory = ProjectMemory(storage_path)
    return memory.get_relevant_context()
