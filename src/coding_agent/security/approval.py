APPROVAL_VALUES = {"s", "si", "y", "yes"}


def is_approved(response: str) -> bool:
    return response.strip().lower() in APPROVAL_VALUES
