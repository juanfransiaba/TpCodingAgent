import os


def read_file(path: str) -> str:
    """Reads the content of a file given its path."""
    try:
        with open(path, "r", encoding="utf-8") as file:
            content = file.read()
        return content
    except FileNotFoundError:
        return f"Error: File not found at {path}"
    except Exception as error:
        return f"Error reading file {path}: {error}"


def write_file(path: str, content: str) -> str:
    """Writes content in a file. Creates or overwrites it."""
    try:
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)

        with open(path, "w", encoding="utf-8") as file:
            file.write(content)

        return f"File written successfully: {path}"
    except Exception as error:
        return f"Error writing file {path}: {error}"


def list_files(directory: str = ".") -> str:
    """Lists files and folders in a directory."""
    try:
        items = os.listdir(directory)

        if not items:
            return f"The directory '{directory}' is empty."

        result = f"Content of '{directory}':\n"

        for item in sorted(items):
            full_path = os.path.join(directory, item)
            marker = "[DIR]" if os.path.isdir(full_path) else "[FILE]"
            result += f"  {marker} {item}\n"

        return result
    except Exception as error:
        return f"Error listing directory {directory}: {error}"
