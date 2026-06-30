import json
import math
from pathlib import Path
from typing import Any

DEFAULT_INDEX_PATH = Path("storage") / "vector_store" / "index.json"


def save_index(
    entries: list[dict[str, Any]],
    index_path: str | Path = DEFAULT_INDEX_PATH,
) -> Path:
    path = Path(index_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(
            {
                "version": 1,
                "entries": entries,
            },
            file,
            indent=2,
            ensure_ascii=True,
        )

    return path


def load_index(index_path: str | Path = DEFAULT_INDEX_PATH) -> list[dict[str, Any]]:
    path = Path(index_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Vector index not found at {path}. Run python -m coding_agent.rag.ingest first."
        )

    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    return list(payload.get("entries", []))


def cosine_similarity(vector_a: list[float], vector_b: list[float]) -> float:
    if len(vector_a) != len(vector_b):
        raise ValueError("Vectors must have the same dimensions.")

    dot_product = sum(a * b for a, b in zip(vector_a, vector_b))
    norm_a = math.sqrt(sum(a * a for a in vector_a))
    norm_b = math.sqrt(sum(b * b for b in vector_b))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot_product / (norm_a * norm_b)


def search_index(
    query_embedding: list[float],
    entries: list[dict[str, Any]],
    top_k: int = 3,
) -> list[dict[str, Any]]:
    scored_entries = []

    for entry in entries:
        embedding = entry.get("embedding", [])

        if not embedding:
            continue

        score = cosine_similarity(query_embedding, embedding)
        scored_entries.append(
            {
                **entry,
                "score": score,
            }
        )

    return sorted(scored_entries, key=lambda item: item["score"], reverse=True)[:top_k]
