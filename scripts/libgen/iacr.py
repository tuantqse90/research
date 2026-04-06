"""Search IACR ePrint archive and return results compatible with SearchResult."""
from __future__ import annotations

import re
from typing import List, Optional

import requests
from bs4 import BeautifulSoup

from .search import SearchResult

IACR_SEARCH = "https://eprint.iacr.org/search"
USER_AGENT = "Mozilla/5.0 (research-workflow/0.1)"


def search_iacr(
    topic: str,
    *,
    max_results: int = 5,
    session: Optional[requests.Session] = None,
) -> List[SearchResult]:
    """Search IACR ePrint and return SearchResult list with PDF links."""
    sess = session or requests.Session()
    sess.headers.update({"User-Agent": USER_AGENT})

    params = {"q": topic}
    resp = sess.get(IACR_SEARCH, params=params, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    results: List[SearchResult] = []

    # Each paper is in a <div class="mb-4"> containing:
    #   - <a class="paperlink" href="/YYYY/NNN"> for the ID
    #   - <strong> for the title
    #   - <span class="fst-italic"> for authors
    for entry_div in soup.find_all("div", class_="mb-4"):
        paper_link = entry_div.find("a", class_="paperlink", href=True)
        if not paper_link:
            continue

        href = paper_link["href"]
        m = re.match(r"^/(\d{4})/(\d+)$", href)
        if not m:
            continue

        year_str, num = m.group(1), m.group(2)
        paper_id = f"{year_str}/{num}"

        # Title from <strong>
        strong = entry_div.find("strong")
        title = strong.get_text(strip=True) if strong else paper_id
        if not title or len(title) < 5:
            title = paper_id

        # Authors from <span class="fst-italic">
        authors_span = entry_div.find("span", class_="fst-italic")
        authors = []
        if authors_span:
            authors_text = authors_span.get_text(strip=True)
            authors = [a.strip() for a in authors_text.split(",") if a.strip()]

        year = int(year_str)
        pdf_url = f"https://eprint.iacr.org/{paper_id}.pdf"

        results.append(
            SearchResult(
                title=title,
                authors=authors,
                year=year,
                pages=None,
                extension="pdf",
                mirror_urls=[pdf_url],
                md5=paper_id.replace("/", "-"),
                publisher="IACR ePrint",
            )
        )

        if len(results) >= max_results:
            break

    return results
