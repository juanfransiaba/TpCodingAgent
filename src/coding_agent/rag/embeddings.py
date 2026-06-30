import os
import re

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

DEFAULT_EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
API_KEY_PATTERN = re.compile(r"sk-[A-Za-z0-9_*\\-]+")


def get_openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not configured. Add it to .env or your environment."
        )

    return OpenAI(api_key=api_key)


def embed_text(
    text: str,
    model: str = DEFAULT_EMBEDDING_MODEL,
) -> list[float]:
    """Generate one embedding with the OpenAI embeddings API."""

    if not text.strip():
        raise ValueError("Cannot embed empty text.")

    client = get_openai_client()
    try:
        response = client.embeddings.create(
            input=text,
            model=model,
        )
    except Exception as error:
        raise RuntimeError(
            f"Error calling OpenAI embeddings API: {sanitize_error(error)}"
        ) from error

    return response.data[0].embedding


def embed_texts(
    texts: list[str],
    model: str = DEFAULT_EMBEDDING_MODEL,
) -> list[list[float]]:
    """Generate embeddings for multiple text chunks."""

    if not texts:
        return []

    if any(not text.strip() for text in texts):
        raise ValueError("Cannot embed empty text.")

    client = get_openai_client()
    try:
        response = client.embeddings.create(
            input=texts,
            model=model,
        )
    except Exception as error:
        raise RuntimeError(
            f"Error calling OpenAI embeddings API: {sanitize_error(error)}"
        ) from error

    return [item.embedding for item in response.data]


def sanitize_error(error: Exception) -> str:
    return API_KEY_PATTERN.sub("sk-***", str(error))
