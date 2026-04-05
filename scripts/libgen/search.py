from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass, field
from typing import List, Optional

import requests
from bs4 import BeautifulSoup

LIBGEN_BASE = "https://libgen.vg"
SEARCH_PATH = "/index.php"
SEARCH_PARAMS_TEMPLATE = [
    ("columns[]", "t"),
    ("columns[]", "a"),
    ("columns[]", "s"),
    ("columns[]", "y"),
    ("columns[]", "p"),
    ("columns[]", "i"),
    ("objects[]", "f"),
    ("objects[]", "e"),
    ("objects[]", "s"),
    ("objects[]", "a"),
    ("objects[]", "p"),
    ("objects[]", "w"),
    ("topics[]", "l"),
    ("topics[]", "a"),
    ("topics[]", "s"),
    ("res", "25"),
    ("filesuns", "all"),
]
USER_AGENT = "Mozilla/5.0 (research-workflow/0.1)"

_MD5_RE = re.compile(r"([a-fA-F0-9]{32})")


@dataclass
class SearchResult:
    title: str
    authors: List[str] = field(default_factory=list)
    publisher: str = ""
    year: Optional[int] = None
    pages: Optional[int] = None
    language: str = ""
    size: str = ""
    extension: str = ""
    mirror_urls: List[str] = field(default_factory=list)
    md5: str = ""


def _safe_int(text: str) -> Optional[int]:
    """Return the first contiguous digit run in text as int, or None."""
    m = re.search(r"\d+", text)
    return int(m.group(0)) if m else None


def _extract_title_from_cell(cell) -> str:
    """Extract the book title from a libgen.vg td[0] cell.

    Strategy 1: read the tooltip `title` attribute of any <a> inside the cell.
    Format: "Add/Edit : ...; ID: ...<br>AUTHOR - TITLE(YEAR, PUBLISHER)".
    The literal "<br>" (not a tag, just text) separates metadata from the
    human-readable "author - title(year, publisher)" portion.

    Strategy 2 (fallback): return the text of the first <a> in the cell
    whose direct children don't contain <i>/<font> (i.e., plain text link).
    """
    for a in cell.find_all("a", title=True):
        tip = a.get("title", "")
        if "<br>" in tip:
            after_br = tip.split("<br>", 1)[1]
            # author (non-greedy) - title (greedy) up to last (YEAR,
            m = re.match(r"(.+?)\s*-\s*(.+)\s*\(\d{4}", after_br)
            if m:
                title = m.group(2).strip()
                if title:
                    return title
    # Fallback: bold <b> text in the cell contains the series/title header.
    b = cell.find("b")
    if b:
        # Strip child <a> tooltip wrappers; keep plain text.
        text = b.get_text(" ", strip=True)
        if text and len(text) > 2:
            return text
    # Last resort: first <a> with plain text longer than 2 chars
    # (skips single-letter badge links like "b").
    for a in cell.find_all("a"):
        if a.find("i") or a.find("font"):
            continue
        text = a.get_text(strip=True)
        if text and len(text) > 2:
            return text
    return ""


def _extract_md5(urls: List[str]) -> str:
    for url in urls:
        m = _MD5_RE.search(url)
        if m:
            return m.group(1).lower()
    return ""


def parse_search_results(html: str) -> List[SearchResult]:
    """Parse a libgen.vg search result HTML page into a SearchResult list.

    libgen.vg renders results in a <table class="table table-striped"> with 9
    data columns: [Title-stack, Author(s), Publisher, Year, Language, Pages,
    Size, Ext., Mirrors].
    """
    soup = BeautifulSoup(html, "html.parser")
    results: List[SearchResult] = []

    table = None
    for t in soup.find_all("table"):
        classes = t.get("class") or []
        if "table-striped" in classes:
            table = t
            break
    if table is None:
        return results

    rows = table.find_all("tr")[1:]  # skip header
    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 9:
            continue

        title = _extract_title_from_cell(cells[0])
        authors_text = cells[1].get_text(" ", strip=True)
        publisher = cells[2].get_text(" ", strip=True)
        year = _safe_int(cells[3].get_text(strip=True))
        language = cells[4].get_text(strip=True)
        pages_text = cells[5].get_text(strip=True)
        pages = _safe_int(pages_text.split("/")[0]) if pages_text else None
        size = cells[6].get_text(strip=True)
        extension = cells[7].get_text(strip=True)

        mirror_urls: List[str] = []
        for a in cells[8].find_all("a", href=True):
            href = a["href"]
            if href.startswith("http"):
                mirror_urls.append(href)
            elif href.startswith("/"):
                # libgen.vg native mirrors like /ads.php?md5=... — resolve
                # against the search base. These are usually the most reliable.
                mirror_urls.append(LIBGEN_BASE + href)
        # Prioritize libgen.vg native mirror (most likely to work without JS).
        mirror_urls.sort(key=lambda u: 0 if LIBGEN_BASE in u else 1)

        md5 = _extract_md5(mirror_urls)

        if not title or not extension:
            continue

        results.append(
            SearchResult(
                title=title,
                authors=[a.strip() for a in authors_text.split(",") if a.strip()],
                publisher=publisher,
                year=year,
                pages=pages,
                language=language,
                size=size,
                extension=extension,
                mirror_urls=mirror_urls,
                md5=md5,
            )
        )
    return results


def search(topic: str, *, session: Optional[requests.Session] = None) -> List[SearchResult]:
    """HTTP search on libgen.vg with retry + backoff.

    Respects HTTPS_PROXY / HTTP_PROXY / ALL_PROXY env vars (requests default),
    which lets callers route through a SOCKS5 tor proxy when needed.
    """
    sess = session or requests.Session()
    sess.headers.update({"User-Agent": USER_AGENT})
    params = [("req", topic)] + list(SEARCH_PARAMS_TEMPLATE)

    last_exc: Optional[Exception] = None
    for attempt in range(3):
        try:
            resp = sess.get(LIBGEN_BASE + SEARCH_PATH, params=params, timeout=60)
            resp.raise_for_status()
            return parse_search_results(resp.text)
        except requests.RequestException as e:
            last_exc = e
            time.sleep(2**attempt)
    raise RuntimeError(f"libgen search failed after 3 attempts: {last_exc}")
