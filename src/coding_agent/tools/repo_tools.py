from pathlib import Path

IGNORED_DIRS = {
    ".git",
    ".idea",
    ".venv",
    ".venv1",
    "__pycache__",
    "venv",
    "node_modules",
    "build",
    "dist",
    ".gradle",
}

SEARCH_EXTENSIONS = {
    ".py",
    ".md",
    ".txt",
    ".yaml",
    ".yml",
    ".json",
    ".toml",
    ".csv",
}

MAX_SEARCH_RESULTS = 50
MAX_FILE_CHARS = 20_000


def tree_files(directory: str = ".", max_depth: int = 4) -> str:
    """Return a compact tree of files and folders."""

    root = Path(directory)

    if not root.exists():
        return f"Error: directory not found: {directory}"

    if not root.is_dir():
        return f"Error: not a directory: {directory}"

    lines = [root.as_posix()]
    add_tree_lines(root, root, lines, current_depth=0, max_depth=max_depth)
    return "\n".join(lines)


def search_code(query: str, directory: str = ".") -> str:
    """Search for a string in code and documentation files."""

    if not query.strip():
        return "Error: query cannot be empty."

    root = Path(directory)

    if not root.exists():
        return f"Error: directory not found: {directory}"

    matches: list[str] = []
    query_lower = query.lower()

    for path in iter_searchable_files(root):
        try:
            with path.open("r", encoding="utf-8", errors="replace") as file:
                for line_number, line in enumerate(file, 1):
                    if query_lower in line.lower():
                        relative_path = path.relative_to(root).as_posix()
                        matches.append(
                            f"{relative_path}:{line_number}: {line.strip()}"
                        )

                    if len(matches) >= MAX_SEARCH_RESULTS:
                        return "\n".join(matches)
        except OSError as error:
            matches.append(f"{path.as_posix()}: error reading file: {error}")

    if not matches:
        return f"No matches found for: {query}"

    return "\n".join(matches)


def view_file(
    path: str,
    start_line: int | None = None,
    end_line: int | None = None,
) -> str:
    """Read a full file or a numbered line range."""

    file_path = Path(path)

    if not file_path.exists():
        return f"Error: file not found: {path}"

    if not file_path.is_file():
        return f"Error: not a file: {path}"

    try:
        lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as error:
        return f"Error reading file {path}: {error}"

    if start_line is None and end_line is None:
        content = "\n".join(lines)
        if len(content) > MAX_FILE_CHARS:
            return content[:MAX_FILE_CHARS] + "\n...[truncated]"
        return content

    start = max((start_line or 1), 1)
    end = min((end_line or len(lines)), len(lines))

    if start > end:
        return f"Error: invalid line range {start}-{end}"

    selected = [
        f"{line_number}: {lines[line_number - 1]}"
        for line_number in range(start, end + 1)
    ]
    return "\n".join(selected)


def add_tree_lines(
    root: Path,
    current: Path,
    lines: list[str],
    current_depth: int,
    max_depth: int,
) -> None:
    if current_depth >= max_depth:
        return

    children = [
        child
        for child in sorted(current.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower()))
        if not should_ignore(child)
    ]

    for child in children:
        indent = "  " * (current_depth + 1)
        marker = "[D]" if child.is_dir() else "[F]"
        relative_path = child.relative_to(root).as_posix()
        lines.append(f"{indent}{marker} {relative_path}")

        if child.is_dir():
            add_tree_lines(root, child, lines, current_depth + 1, max_depth)


def iter_searchable_files(root: Path):
    for path in root.rglob("*"):
        if should_ignore(path):
            continue

        if not path.is_file():
            continue

        if path.suffix.lower() not in SEARCH_EXTENSIONS:
            continue

        yield path


def should_ignore(path: Path) -> bool:
    return any(part in IGNORED_DIRS for part in path.parts)
