from __future__ import annotations

import re
import time
from pathlib import Path
from typing import List, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

USER_AGENT = "Mozilla/5.0 (research-workflow/0.1)"

# Text patterns that typically label a direct-download link on mirror pages.
_GET_TEXT_RE = re.compile(r"^\s*(get|download|get\s+book|direct\s+download)\s*$", re.I)


def resolve_direct_url(mirror_url: str, *, session: requests.Session) -> Optional[str]:
    """Fetch a mirror page and return a direct-download URL, or None.

    Handles the common libgen-ecosystem mirrors (annas-archive.gl, libgen.pw,
    randombook.org, library.lol, books.ms, etc.) by looking for:
      1. An <a> whose visible text matches GET / DOWNLOAD / etc.
      2. An <a> whose href points at a CDN-style path (get.php, fast_download,
         cdn, download).
    Returns None if no plausible download link is found.
    """
    try:
        resp = session.get(mirror_url, timeout=60, allow_redirects=True)
        resp.raise_for_status()
    except requests.RequestException:
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    base = resp.url

    def _is_real_href(href: str) -> bool:
        if not href:
            return False
        stripped = href.strip()
        return stripped and stripped != "#" and not stripped.startswith("javascript:")

    # Strategy 1: href pointing at a CDN-style download endpoint.
    # Checked first because it's the specific libgen.vg direct link
    # (get.php?md5=...&key=...), avoiding confusion with nav "DOWNLOAD" links.
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not _is_real_href(href):
            continue
        if any(tok in href for tok in ("get.php", "fast_download", "/cdn/", "download.php", "/download/")):
            return _absolutize(base, href)

    # Strategy 2: visible text match on a real href.
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not _is_real_href(href):
            continue
        text = a.get_text(strip=True)
        if _GET_TEXT_RE.match(text):
            return _absolutize(base, href)

    return None


def _absolutize(base: str, href: str) -> str:
    if href.startswith("http://") or href.startswith("https://"):
        return href
    if href.startswith("//"):
        return "https:" + href
    if href.startswith("/"):
        parsed = urlparse(base)
        return f"{parsed.scheme}://{parsed.netloc}{href}"
    return urljoin(base, href)


def download_file(url: str, dest: Path, *, session: requests.Session) -> bool:
    """Stream-download a URL to dest with a progress bar. Returns True on success.

    Validates the result has plausible file magic bytes (%PDF- for PDF,
    PK\\x03\\x04 for EPUB/ZIP). This catches HTML error pages served as 200.
    """
    try:
        with session.get(url, stream=True, timeout=120) as resp:
            resp.raise_for_status()
            total = int(resp.headers.get("content-length", 0))
            dest.parent.mkdir(parents=True, exist_ok=True)
            with open(dest, "wb") as f, tqdm(
                total=total, unit="B", unit_scale=True, desc=dest.name
            ) as bar:
                for chunk in resp.iter_content(chunk_size=64 * 1024):
                    if chunk:
                        f.write(chunk)
                        bar.update(len(chunk))
        if dest.stat().st_size < 1024:
            dest.unlink(missing_ok=True)
            return False
        if not _looks_like_book(dest):
            dest.unlink(missing_ok=True)
            return False
        return True
    except requests.RequestException:
        if dest.exists():
            dest.unlink()
        return False


def _looks_like_book(path: Path) -> bool:
    """Return True if the file starts with PDF or ZIP/EPUB magic bytes."""
    with open(path, "rb") as f:
        head = f.read(8)
    return head.startswith(b"%PDF-") or head.startswith(b"PK\x03\x04")


def try_mirrors(mirror_urls: List[str], dest: Path, *, session: requests.Session) -> bool:
    """Walk mirror URLs in order until one yields a successful download."""
    for mirror in mirror_urls:
        direct = resolve_direct_url(mirror, session=session)
        if not direct:
            continue
        if download_file(direct, dest, session=session):
            return True
        time.sleep(1)
    return False


def new_session() -> requests.Session:
    """Create a requests session. Respects HTTPS_PROXY / ALL_PROXY env vars,
    so callers can route through a SOCKS5 tor proxy by setting e.g.
    HTTPS_PROXY=socks5h://127.0.0.1:9050 before invoking the CLI.
    """
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT})
    return s
