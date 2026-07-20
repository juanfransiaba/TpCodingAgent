import shlex
from pathlib import Path


def check_permissions(tool_name: str, args: dict, config: dict) -> tuple[bool, str]:
    """Checks whether a tool call violates the configured policies."""

    if tool_name == "run_command":
        return check_command(args.get("command", ""), config)

    if tool_name in ("read_file", "write_file", "view_file"):
        return check_path(tool_name, args.get("path", ""), config)

    if tool_name in ("list_files", "tree_files", "search_code"):
        return check_path(tool_name, args.get("directory", "."), config)

    return True, "OK"


def normalize_tool_args(tool_name: str, args: dict, config: dict) -> dict:
    """Resolve path arguments against the configured workspace."""

    normalized_args = args.copy()

    if tool_name in ("read_file", "write_file", "view_file") and "path" in args:
        normalized_args["path"] = str(resolve_workspace_path(args["path"], config))

    if tool_name in ("list_files", "tree_files", "search_code"):
        normalized_args["directory"] = str(
            resolve_workspace_path(args.get("directory", "."), config)
        )

    if tool_name in (
        "remember_decision",
        "remember_command",
        "memory_context",
        "read_project_memory",
    ):
        normalized_args["storage_path"] = config.get("memory", {}).get(
            "path",
            "memory/project_memory.json",
        )

    if tool_name == "run_command" and "command" in args:
        workspace = get_workspace(config)
        normalized_args["command"] = (
            f"cd {shlex.quote(str(workspace))} && {args['command']}"
        )

    return normalized_args


def requires_approval(tool_name: str, args: dict, config: dict) -> bool:
    """Checks whether a tool call needs explicit user approval."""

    if tool_name != "run_command":
        return False

    command = args.get("command", "")
    approval_patterns = config.get("commands", {}).get("require_approval", [])

    return any(pattern in command for pattern in approval_patterns)


def check_command(command: str, config: dict) -> tuple[bool, str]:
    denied_commands = config.get("commands", {}).get("deny", [])

    for denied in denied_commands:
        if denied in command:
            return False, f"Command blocked by policy: '{denied}'"

    return True, "OK"


def check_path(tool_name: str, raw_path: str, config: dict) -> tuple[bool, str]:
    workspace = get_workspace(config)
    resolved_path = resolve_workspace_path(raw_path, config)

    try:
        relative_path = resolved_path.relative_to(workspace).as_posix()
    except ValueError:
        return False, f"Path outside workspace: {resolved_path}"

    permission_type = "write" if tool_name == "write_file" else "read"
    denied_paths = config.get("permissions", {}).get(permission_type, {}).get("deny", [])

    for denied in denied_paths:
        if matches_denied_path(relative_path, denied):
            return False, f"Path blocked by policy: '{denied}'"

    return True, "OK"


def get_workspace(config: dict) -> Path:
    return Path(config.get("workspace", ".")).resolve()


def resolve_workspace_path(raw_path: str, config: dict) -> Path:
    workspace = get_workspace(config)
    target_path = Path(raw_path)

    if not target_path.is_absolute():
        target_path = workspace / target_path

    return target_path.resolve()


def matches_denied_path(relative_path: str, pattern: str) -> bool:
    if pattern.endswith("/**"):
        prefix = pattern.removesuffix("/**")
        return relative_path.startswith(prefix)

    if pattern.startswith("**/*."):
        extension = pattern.removeprefix("**/*")
        return relative_path.endswith(extension)

    return relative_path == pattern or relative_path.startswith(pattern.rstrip("/") + "/")
