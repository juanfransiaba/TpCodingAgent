from pathlib import Path

from coding_agent.rag.embeddings import embed_text
from coding_agent.rag.ingest import find_repo_root, resolve_repo_path
from coding_agent.rag.vector_store import DEFAULT_INDEX_PATH, load_index, search_index


class LocalRetriever:
    """Retriever adapter over the local JSON vector index."""

    def __init__(self, index_path: str | Path = DEFAULT_INDEX_PATH):
        self.index_path = index_path

    def search(self, query: str, top_k: int = 3) -> str:
        return rag_search(query=query, top_k=top_k, index_path=self.index_path)


def rag_search(
    query: str,
    top_k: int = 3,
    index_path: str | Path = DEFAULT_INDEX_PATH,
) -> str:
    """Retrieve relevant local documentation chunks from the vector index."""

    if not query.strip():
        return "Error: query cannot be empty."

    if top_k <= 0:
        return "Error: top_k must be greater than zero."

    repo_root = find_repo_root()
    resolved_index_path = resolve_repo_path(index_path, repo_root)

    try:
        entries = load_index(resolved_index_path)
    except FileNotFoundError as error:
        return str(error)
    except Exception as error:
        return f"Error loading vector index: {error}"

    try:
        query_embedding = embed_text(query)
    except Exception as error:
        return f"Error generating query embedding: {error}"

    results = search_index(query_embedding, entries, top_k=top_k)

    if not results:
        return "No RAG results found."

    return "\n\n".join(format_result(result) for result in results)


def format_result(result: dict) -> str:
    return "\n".join(
        [
            f"Fuente: {result.get('source', 'unknown')}",
            f"Chunk: {result.get('chunk_id', 'unknown')}",
            f"Score: {result.get('score', 0.0):.2f}",
            "Contenido:",
            result.get("text", ""),
        ]
    )
