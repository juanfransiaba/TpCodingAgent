from pathlib import Path

from coding_agent.rag.chunker import Chunk, chunk_markdown_file
from coding_agent.rag.embeddings import DEFAULT_EMBEDDING_MODEL, embed_texts
from coding_agent.rag.vector_store import DEFAULT_INDEX_PATH, save_index

DEFAULT_RAG_DOCS_DIR = Path("rag_docs")
DEFAULT_CHUNK_SIZE = 800
DEFAULT_OVERLAP = 150


def ingest_documents(
    docs_dir: str | Path = DEFAULT_RAG_DOCS_DIR,
    index_path: str | Path = DEFAULT_INDEX_PATH,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> tuple[int, int, Path]:
    """Read markdown docs, embed chunks, and save a local JSON vector index."""

    repo_root = find_repo_root()
    resolved_docs_dir = resolve_repo_path(docs_dir, repo_root)
    resolved_index_path = resolve_repo_path(index_path, repo_root)

    if not resolved_docs_dir.exists():
        raise FileNotFoundError(f"RAG docs directory not found: {resolved_docs_dir}")

    markdown_files = sorted(resolved_docs_dir.rglob("*.md"))

    if not markdown_files:
        raise FileNotFoundError(f"No .md files found in {resolved_docs_dir}")

    chunks: list[Chunk] = []

    for path in markdown_files:
        chunks.extend(
            chunk_markdown_file(
                path=path,
                repo_root=repo_root,
                chunk_size=chunk_size,
                overlap=overlap,
            )
        )

    embeddings = embed_texts([chunk.text for chunk in chunks])
    entries = [
        {
            "source": chunk.source,
            "chunk_id": chunk.chunk_id,
            "text": chunk.text,
            "embedding": embedding,
            "embedding_model": DEFAULT_EMBEDDING_MODEL,
        }
        for chunk, embedding in zip(chunks, embeddings)
    ]

    saved_path = save_index(entries, resolved_index_path)
    return len(markdown_files), len(chunks), saved_path


def find_repo_root() -> Path:
    current = Path(__file__).resolve()

    for parent in current.parents:
        if (parent / "agent.config.yaml").exists():
            return parent

    return Path.cwd()


def resolve_repo_path(path: str | Path, repo_root: Path) -> Path:
    resolved_path = Path(path)

    if resolved_path.is_absolute():
        return resolved_path

    return repo_root / resolved_path


def main() -> None:
    try:
        docs_count, chunks_count, index_path = ingest_documents()
    except Exception as error:
        print(f"RAG ingest failed: {error}")
        raise SystemExit(1) from error

    print(f"Indexed documents: {docs_count}")
    print(f"Indexed chunks: {chunks_count}")
    print(f"Index saved to: {index_path}")


if __name__ == "__main__":
    main()
