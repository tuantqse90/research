"""Search arXiv and return results compatible with SearchResult."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import List, Optional

import requests

from .search import SearchResult

ARXIV_API = "https://export.arxiv.org/api/query"
USER_AGENT = "Mozilla/5.0 (research-workflow/0.1)"

# Atom namespace
_NS = {"atom": "http://www.w3.org/2005/Atom"}


def _text(el: Optional[ET.Element]) -> str:
    return (el.text or "").strip() if el is not None else ""


def _extract_year(published: str) -> Optional[int]:
    m = re.match(r"(\d{4})", published)
    return int(m.group(1)) if m else None


def _extract_arxiv_id(entry_id: str) -> str:
    """Extract arxiv ID from URL like http://arxiv.org/abs/2301.12345v2."""
    m = re.search(r"abs/(.+?)(?:v\d+)?$", entry_id)
    return m.group(1) if m else entry_id.rsplit("/", 1)[-1]


def search_arxiv(
    topic: str,
    *,
    max_results: int = 5,
    session: Optional[requests.Session] = None,
) -> List[SearchResult]:
    """Query arXiv API and return SearchResult list (PDF links included)."""
    sess = session or requests.Session()
    sess.headers.update({"User-Agent": USER_AGENT})

    # Quote the topic as a phrase for better relevance
    quoted = f'"{topic}"'
    params = {
        "search_query": f"all:{quoted}",
        "start": 0,
        "max_results": max_results,
        "sortBy": "relevance",
        "sortOrder": "descending",
    }

    resp = sess.get(ARXIV_API, params=params, timeout=30)
    resp.raise_for_status()

    root = ET.fromstring(resp.text)
    results: List[SearchResult] = []

    for entry in root.findall("atom:entry", _NS):
        title = _text(entry.find("atom:title", _NS)).replace("\n", " ")
        if not title:
            continue

        authors = []
        for author_el in entry.findall("atom:author", _NS):
            name = _text(author_el.find("atom:name", _NS))
            if name:
                authors.append(name)

        published = _text(entry.find("atom:published", _NS))
        year = _extract_year(published)

        entry_id = _text(entry.find("atom:id", _NS))
        arxiv_id = _extract_arxiv_id(entry_id)
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}"
        abs_url = f"https://arxiv.org/abs/{arxiv_id}"

        results.append(
            SearchResult(
                title=title,
                authors=authors,
                year=year,
                pages=None,
                extension="pdf",
                mirror_urls=[pdf_url],
                md5=arxiv_id,  # use arxiv ID as unique key
                publisher="arXiv",
            )
        )

    return results
