import re
import unicodedata


def slugify(text: str) -> str:
    """Lowercase, strip diacritics, replace non-alphanumerics with '-'."""
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    lowered = ascii_text.lower()
    dashed = re.sub(r"[^a-z0-9]+", "-", lowered)
    return dashed.strip("-")


def dated_dirname(date_str: str, topic: str) -> str:
    """e.g. ('2026-04-06', 'hunt') -> '2026-04-06_hunt'."""
    return f"{date_str}_{slugify(topic)}"
