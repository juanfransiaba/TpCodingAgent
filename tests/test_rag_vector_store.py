import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from coding_agent.rag.chunker import chunk_text
from coding_agent.rag.vector_store import load_index, save_index, search_index


class RagVectorStoreTests(unittest.TestCase):
    def test_chunks_and_searches_local_index(self):
        chunks = chunk_text(
            "alpha beta gamma delta epsilon",
            source="rag_docs/example.md",
            chunk_size=12,
            overlap=3,
        )

        self.assertGreater(len(chunks), 1)

        with tempfile.TemporaryDirectory() as temp_dir:
            index_path = Path(temp_dir) / "index.json"
            entries = [
                {
                    "source": "rag_docs/alpha.md",
                    "chunk_id": 0,
                    "text": "alpha",
                    "embedding": [1.0, 0.0],
                },
                {
                    "source": "rag_docs/beta.md",
                    "chunk_id": 1,
                    "text": "beta",
                    "embedding": [0.0, 1.0],
                },
            ]

            save_index(entries, index_path)
            loaded_entries = load_index(index_path)
            results = search_index([1.0, 0.0], loaded_entries, top_k=1)

            self.assertEqual(results[0]["source"], "rag_docs/alpha.md")


if __name__ == "__main__":
    unittest.main()
