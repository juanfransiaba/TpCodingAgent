from coding_agent.security.approval import is_approved


def ask_permission(tool_name: str, args: dict) -> bool:
    """Asks the user for permission before executing risky tools."""
    print(f"\nApproval required for: {tool_name}")
    print(f"   Arguments: {args}")

    response = input("   Approve? [s/n]: ")

    return is_approved(response)
