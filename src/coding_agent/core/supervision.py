def ask_permission(tool_name: str, args: dict) -> bool:
    """Asks the user for permission before executing risky tools."""
    print(f"\nApproval required for: {tool_name}")
    print(f"   Arguments: {args}")

    response = input("   Approve? [s/n]: ").strip().lower()

    return response in ("s", "si", "y", "yes")
