import unicodedata


APPROVAL_VALUES = {
    "s",
    "si",
    "y",
    "yes",
    "ok",
    "dale",
    "aprobado",
}


def is_approved(response: str) -> bool:
    return normalize_response(response) in APPROVAL_VALUES


def normalize_response(response: str) -> str:
    normalized = unicodedata.normalize("NFKD", response.strip().lower())
    return "".join(
        character
        for character in normalized
        if not unicodedata.combining(character)
    )
