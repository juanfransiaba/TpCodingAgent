from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Chunk:
    source: str
    chunk_id: int
    text: str


def chunk_text(
    text: str,
    source: str,
    chunk_size: int = 800,
    overlap: int = 150,
) -> list[Chunk]:
    """Split text into overlapping character chunks."""

    normalized_text = text.strip()

    if not normalized_text:
        return []

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")

    if overlap < 0:
        raise ValueError("overlap cannot be negative")

    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    chunks: list[Chunk] = []
    start = 0
    chunk_id = 0

    while start < len(normalized_text):
        end = min(start + chunk_size, len(normalized_text))
        chunk = normalized_text[start:end].strip()

        if chunk:
            chunks.append(
                Chunk(
                    source=source,
                    chunk_id=chunk_id,
                    text=chunk,
                )
            )
            chunk_id += 1

        if end >= len(normalized_text):
            break

        start = end - overlap

    return chunks


def chunk_markdown_file(
    path: Path,
    repo_root: Path,
    chunk_size: int = 800,
    overlap: int = 150,
) -> list[Chunk]:
    text = path.read_text(encoding="utf-8", errors="replace")
    source = path.relative_to(repo_root).as_posix()
    return chunk_text(
        text=text,
        source=source,
        chunk_size=chunk_size,
        overlap=overlap,
    )
