from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from pypdf import PdfReader


def _flatten_outline(outline, depth: int = 0) -> List[str]:
    """Recursively flatten a pypdf outline into indented title strings."""
    lines: List[str] = []
    for item in outline:
        if isinstance(item, list):
            lines.extend(_flatten_outline(item, depth + 1))
        else:
            title = getattr(item, "title", None)
            if title:
                lines.append("  " * depth + str(title))
    return lines


def extract_excerpt(
    pdf_path: Path,
    *,
    max_pages: int = 30,
    metadata_header: Optional[dict] = None,
) -> str:
    """Return a text excerpt: metadata + TOC + first N pages.

    Raises on unrecoverable read errors so the caller can mark status.
    """
    reader = PdfReader(str(pdf_path))
    parts: List[str] = []

    parts.append("=== METADATA ===")
    if metadata_header:
        for k, v in metadata_header.items():
            parts.append(f"{k}: {v}")
    parts.append("")

    parts.append("=== TABLE OF CONTENTS ===")
    try:
        outline = reader.outline  # pypdf exposes outline as nested list
        toc_lines = _flatten_outline(outline) if outline else []
        if toc_lines:
            parts.extend(toc_lines)
        else:
            parts.append("(no outline available)")
    except Exception as e:
        parts.append(f"(TOC extraction failed: {e})")
    parts.append("")

    parts.append(f"=== FIRST {max_pages} PAGES ===")
    total = len(reader.pages)
    limit = min(max_pages, total)
    for i in range(limit):
        try:
            text = reader.pages[i].extract_text() or ""
        except Exception:
            text = ""
        parts.append(f"--- page {i + 1} ---")
        parts.append(text.strip())
    return "\n".join(parts)


def write_excerpt(
    pdf_path: Path,
    excerpt_path: Path,
    *,
    max_pages: int = 30,
    metadata_header: Optional[dict] = None,
) -> None:
    text = extract_excerpt(pdf_path, max_pages=max_pages, metadata_header=metadata_header)
    excerpt_path.parent.mkdir(parents=True, exist_ok=True)
    excerpt_path.write_text(text, encoding="utf-8")
