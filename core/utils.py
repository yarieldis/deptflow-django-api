from django.utils.text import slugify


def normalize_code(value: str) -> str:
    """Normalize a business code for unique-index stability (lowercase slug)."""
    return slugify(value or "")
