# Libgen Research Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a `/research <topic>` slash command that fetches top-5 libgen books on a topic, extracts TOC + first 30 pages, and produces a synthesized `idea.md` with per-book summaries.

**Architecture:** Python handles deterministic work (HTTP, HTML parsing, PDF download/extract). Claude orchestrates via a slash command, consumes the structured artifacts, and does all reasoning (per-book summaries + cross-source synthesis).

**Tech Stack:** Python 3.11+, `requests`, `beautifulsoup4`, `pypdf`, `tqdm`, `pytest`. Claude Code slash command.

---

## File Structure

**Created:**
- `scripts/libgen_fetch.py` — CLI entrypoint, orchestrates search → download → extract → metadata
- `scripts/libgen/__init__.py` — package marker
- `scripts/libgen/slug.py` — slugify + date helpers
- `scripts/libgen/search.py` — libgen.vg HTML parser + HTTP search
- `scripts/libgen/download.py` — mirror resolver + file downloader
- `scripts/libgen/extract.py` — PDF TOC + first-N-pages extractor
- `scripts/libgen/metadata.py` — metadata.json writer
- `scripts/requirements.txt`
- `.claude/commands/research.md` — slash command prompt
- `tests/__init__.py`
- `tests/test_slug.py`
- `tests/test_search_parser.py`
- `tests/fixtures/libgen_search.html` — captured HTML fixture
- `.gitignore`

Each `libgen/*.py` module has one responsibility and is independently testable. `libgen_fetch.py` is the thin wiring layer.

---

## Task 0: Repo init + scaffolding

**Files:**
- Create: `.gitignore`
- Create: `scripts/__init__.py` (empty)
- Create: `scripts/libgen/__init__.py` (empty)
- Create: `tests/__init__.py` (empty)

- [ ] **Step 1: Initialize git repo**

Run:
```bash
cd /Users/s6klabs/Desktop/research
git init
git add docs/
git commit -m "docs: add design spec and implementation plan"
```

- [ ] **Step 2: Create `.gitignore`**

```gitignore
__pycache__/
*.pyc
.venv/
venv/
.pytest_cache/
topics/
*.pdf
*.epub
!tests/fixtures/*
.DS_Store
```

- [ ] **Step 3: Create empty package markers**

```bash
mkdir -p scripts/libgen tests/fixtures
touch scripts/__init__.py scripts/libgen/__init__.py tests/__init__.py
```

- [ ] **Step 4: Commit scaffolding**

```bash
git add .gitignore scripts/__init__.py scripts/libgen/__init__.py tests/__init__.py
git commit -m "chore: initial project scaffolding"
```

---

## Task 1: Dependencies + virtualenv

**Files:**
- Create: `scripts/requirements.txt`

- [ ] **Step 1: Write `scripts/requirements.txt`**

```
requests>=2.31
beautifulsoup4>=4.12
pypdf>=4.0
tqdm>=4.66
pytest>=8.0
```

- [ ] **Step 2: Create virtualenv and install**

Run:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r scripts/requirements.txt
```

Expected: all packages install without error.

- [ ] **Step 3: Verify pytest runs**

Run: `pytest --version`
Expected: `pytest 8.x`

- [ ] **Step 4: Commit**

```bash
git add scripts/requirements.txt
git commit -m "chore: add Python dependencies"
```

---

## Task 2: Slugify utility (TDD)

**Files:**
- Create: `scripts/libgen/slug.py`
- Test: `tests/test_slug.py`

- [ ] **Step 1: Write failing tests**

`tests/test_slug.py`:
```python
from scripts.libgen.slug import slugify, dated_dirname


def test_slugify_ascii_lowercases_and_dashes():
    assert slugify("Artificial Intelligence") == "artificial-intelligence"


def test_slugify_strips_diacritics():
    assert slugify("săn bắn") == "san-ban"


def test_slugify_removes_punctuation():
    assert slugify("hunt, track & kill!") == "hunt-track-kill"


def test_slugify_collapses_whitespace():
    assert slugify("   multi   space  ") == "multi-space"


def test_dated_dirname_basic():
    assert dated_dirname("2026-04-06", "hunt") == "2026-04-06_hunt"
```

- [ ] **Step 2: Run tests — verify they fail**

Run: `pytest tests/test_slug.py -v`
Expected: ImportError / ModuleNotFoundError for `scripts.libgen.slug`.

- [ ] **Step 3: Implement `scripts/libgen/slug.py`**

```python
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
```

- [ ] **Step 4: Run tests — verify they pass**

Run: `pytest tests/test_slug.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/libgen/slug.py tests/test_slug.py
git commit -m "feat: slugify utility with diacritic stripping"
```

---

## Task 3: Capture libgen HTML fixture

**Files:**
- Create: `tests/fixtures/libgen_search.html`

- [ ] **Step 1: Capture a real search result page**

Run:
```bash
curl -sL 'https://libgen.vg/index.php?req=python&columns%5B%5D=t&columns%5B%5D=a&columns%5B%5D=s&columns%5B%5D=y&columns%5B%5D=p&columns%5B%5D=i&objects%5B%5D=f&objects%5B%5D=e&objects%5B%5D=s&objects%5B%5D=a&objects%5B%5D=p&objects%5B%5D=w&topics%5B%5D=l&topics%5B%5D=a&topics%5B%5D=s&res=25&filesuns=all' \
  -o tests/fixtures/libgen_search.html
```

- [ ] **Step 2: Verify fixture is a real search page**

Run: `wc -l tests/fixtures/libgen_search.html && grep -c '<tr' tests/fixtures/libgen_search.html`
Expected: nonzero line count and at least 10 `<tr` rows.

- [ ] **Step 3: Inspect table structure**

Run: `python3 -c "from bs4 import BeautifulSoup; s=BeautifulSoup(open('tests/fixtures/libgen_search.html'),'html.parser'); t=s.find('table'); print(t.get('class') if t else 'no table'); print([th.get_text(strip=True) for th in s.select('table tr')[0].find_all(['th','td'])][:12])"`

Record the table class and header columns in your notebook — Task 4 will use them. If the structure differs from the assumed one (`Title`, `Author(s)`, `Publisher`, `Year`, `Pages`, `Language`, `Size`, `Extension`, `Mirrors`), adjust selectors in Task 4 accordingly.

- [ ] **Step 4: Commit fixture**

```bash
git add tests/fixtures/libgen_search.html
git commit -m "test: add libgen search HTML fixture"
```

---

## Task 4: Search result parser (TDD)

**Files:**
- Create: `scripts/libgen/search.py`
- Test: `tests/test_search_parser.py`

- [ ] **Step 1: Write failing parser tests**

`tests/test_search_parser.py`:
```python
from pathlib import Path
from scripts.libgen.search import parse_search_results, SearchResult

FIXTURE = Path(__file__).parent / "fixtures" / "libgen_search.html"


def load_fixture() -> str:
    return FIXTURE.read_text(encoding="utf-8")


def test_parse_returns_list_of_results():
    results = parse_search_results(load_fixture())
    assert isinstance(results, list)
    assert len(results) > 0
    assert all(isinstance(r, SearchResult) for r in results)


def test_parse_extracts_required_fields():
    results = parse_search_results(load_fixture())
    first = results[0]
    assert first.title
    assert first.extension.lower() in {"pdf", "epub", "djvu", "mobi", "azw3"}
    assert first.mirror_urls  # non-empty list


def test_parse_year_is_int_or_none():
    results = parse_search_results(load_fixture())
    for r in results:
        assert r.year is None or isinstance(r.year, int)
```

- [ ] **Step 2: Run tests — verify failure**

Run: `pytest tests/test_search_parser.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement `scripts/libgen/search.py`**

```python
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

LIBGEN_BASE = "https://libgen.vg"
SEARCH_PATH = "/index.php"
SEARCH_PARAMS_TEMPLATE = {
    "columns[]": ["t", "a", "s", "y", "p", "i"],
    "objects[]": ["f", "e", "s", "a", "p", "w"],
    "topics[]": ["l", "a", "s"],
    "res": "25",
    "filesuns": "all",
}
USER_AGENT = "Mozilla/5.0 (research-workflow/0.1)"


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
    digits = "".join(ch for ch in text if ch.isdigit())
    return int(digits) if digits else None


def parse_search_results(html: str) -> List[SearchResult]:
    """Parse a libgen.vg search result HTML page into SearchResult list.

    Libgen.vg renders results in a <table> where each data row has cells:
    [#, Author(s), Title, Publisher, Year, Pages, Language, Size, Extension, Mirrors...]
    If the structure shifts, adjust the column indices below.
    """
    soup = BeautifulSoup(html, "html.parser")
    results: List[SearchResult] = []

    # Find the results table (largest table with book rows)
    tables = soup.find_all("table")
    table = None
    for t in tables:
        rows = t.find_all("tr")
        if len(rows) >= 2 and len(rows[1].find_all("td")) >= 8:
            table = t
            break
    if table is None:
        return results

    rows = table.find_all("tr")[1:]  # skip header
    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 9:
            continue
        # Column layout (adjust indices if fixture inspection shows different):
        # 0: id/number, 1: author(s), 2: title, 3: publisher,
        # 4: year, 5: pages, 6: language, 7: size, 8: extension, 9+: mirrors
        authors_text = cells[1].get_text(" ", strip=True)
        title_cell = cells[2]
        title = title_cell.get_text(" ", strip=True)
        # MD5 is often in a link href like ?md5=abcd...
        md5 = ""
        for a in title_cell.find_all("a", href=True):
            href = a["href"]
            if "md5=" in href:
                md5 = href.split("md5=")[-1].split("&")[0].lower()
                break
        publisher = cells[3].get_text(" ", strip=True)
        year = _safe_int(cells[4].get_text(strip=True))
        pages = _safe_int(cells[5].get_text(strip=True))
        language = cells[6].get_text(strip=True)
        size = cells[7].get_text(strip=True)
        extension = cells[8].get_text(strip=True)

        mirror_urls: List[str] = []
        for cell in cells[9:]:
            for a in cell.find_all("a", href=True):
                href = a["href"]
                if href.startswith("http"):
                    mirror_urls.append(href)
                else:
                    mirror_urls.append(urljoin(LIBGEN_BASE, href))

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
    """HTTP search on libgen.vg with retry + backoff."""
    sess = session or requests.Session()
    sess.headers.update({"User-Agent": USER_AGENT})
    params = [("req", topic)]
    for key, values in SEARCH_PARAMS_TEMPLATE.items():
        if isinstance(values, list):
            for v in values:
                params.append((key, v))
        else:
            params.append((key, values))

    last_exc: Optional[Exception] = None
    for attempt in range(3):
        try:
            resp = sess.get(LIBGEN_BASE + SEARCH_PATH, params=params, timeout=30)
            resp.raise_for_status()
            return parse_search_results(resp.text)
        except requests.RequestException as e:
            last_exc = e
            time.sleep(2**attempt)
    raise RuntimeError(f"libgen search failed after 3 attempts: {last_exc}")
```

- [ ] **Step 4: Run parser tests — verify they pass**

Run: `pytest tests/test_search_parser.py -v`
Expected: 3 passed. If a test fails because column indices are wrong, inspect the fixture (`python3 -c "from bs4 import BeautifulSoup; ..."`) and adjust the `cells[i]` indices in `parse_search_results`.

- [ ] **Step 5: Commit**

```bash
git add scripts/libgen/search.py tests/test_search_parser.py
git commit -m "feat: libgen search HTTP + HTML parser"
```

---

## Task 5: Mirror resolver + downloader

**Files:**
- Create: `scripts/libgen/download.py`

- [ ] **Step 1: Implement `scripts/libgen/download.py`**

No unit test — this module does network + filesystem I/O which is integration-tested via Task 9 smoke test. Code must be simple enough to review by eye.

```python
from __future__ import annotations

import time
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

USER_AGENT = "Mozilla/5.0 (research-workflow/0.1)"


def resolve_direct_url(mirror_url: str, *, session: requests.Session) -> Optional[str]:
    """Follow a libgen mirror page and find the GET download link.

    Mirror pages (books.ms, library.lol) typically contain a <a> with text
    'GET' pointing at a direct CDN URL. Returns None if not found.
    """
    try:
        resp = session.get(mirror_url, timeout=30, allow_redirects=True)
        resp.raise_for_status()
    except requests.RequestException:
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    # Primary pattern: <a> with text GET
    for a in soup.find_all("a", href=True):
        text = a.get_text(strip=True).upper()
        if text == "GET":
            href = a["href"]
            if href.startswith("http"):
                return href
            parsed = urlparse(resp.url)
            return f"{parsed.scheme}://{parsed.netloc}{href if href.startswith('/') else '/' + href}"
    # Fallback: first link to cdn-like host
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("http") and any(k in href for k in ("cdn", "get.php", "download")):
            return href
    return None


def download_file(url: str, dest: Path, *, session: requests.Session) -> bool:
    """Stream download with progress bar. Returns True on success."""
    try:
        with session.get(url, stream=True, timeout=60) as resp:
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
        return True
    except requests.RequestException:
        if dest.exists():
            dest.unlink()
        return False


def try_mirrors(mirror_urls: List[str], dest: Path, *, session: requests.Session) -> bool:
    """Walk mirrors in order until one succeeds."""
    for mirror in mirror_urls:
        direct = resolve_direct_url(mirror, session=session)
        if not direct:
            continue
        if download_file(direct, dest, session=session):
            return True
        time.sleep(1)
    return False


def new_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT})
    return s
```

- [ ] **Step 2: Smoke-check the module imports**

Run: `python3 -c "from scripts.libgen.download import resolve_direct_url, download_file, try_mirrors, new_session; print('ok')"`
Expected: `ok`.

- [ ] **Step 3: Commit**

```bash
git add scripts/libgen/download.py
git commit -m "feat: mirror resolver and file downloader"
```

---

## Task 6: PDF excerpt extractor

**Files:**
- Create: `scripts/libgen/extract.py`

- [ ] **Step 1: Implement `scripts/libgen/extract.py`**

```python
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
```

- [ ] **Step 2: Verify import**

Run: `python3 -c "from scripts.libgen.extract import extract_excerpt, write_excerpt; print('ok')"`
Expected: `ok`.

- [ ] **Step 3: Commit**

```bash
git add scripts/libgen/extract.py
git commit -m "feat: PDF TOC and first-pages excerpt extractor"
```

---

## Task 7: Metadata writer

**Files:**
- Create: `scripts/libgen/metadata.py`

- [ ] **Step 1: Implement `scripts/libgen/metadata.py`**

```python
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional


@dataclass
class SourceRecord:
    id: str
    title: str
    authors: List[str]
    year: Optional[int]
    pages: Optional[int]
    extension: str
    md5: str
    libgen_mirrors: List[str]
    local_path: str = ""
    excerpt_path: str = ""
    status: str = "pending"  # pending | ok | download_failed | extract_failed
    note: str = ""


@dataclass
class RunMetadata:
    topic: str
    fetched_at: str
    out_dir: str
    sources: List[SourceRecord] = field(default_factory=list)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_metadata(meta: RunMetadata, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "topic": meta.topic,
        "fetched_at": meta.fetched_at,
        "out_dir": meta.out_dir,
        "sources": [asdict(s) for s in meta.sources],
    }
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
```

- [ ] **Step 2: Verify import**

Run: `python3 -c "from scripts.libgen.metadata import RunMetadata, SourceRecord, write_metadata, now_iso; print('ok')"`
Expected: `ok`.

- [ ] **Step 3: Commit**

```bash
git add scripts/libgen/metadata.py
git commit -m "feat: metadata record types and JSON writer"
```

---

## Task 8: CLI entrypoint — `libgen_fetch.py`

**Files:**
- Create: `scripts/libgen_fetch.py`

- [ ] **Step 1: Implement the CLI**

```python
#!/usr/bin/env python3
"""Fetch top-N books from libgen.vg for a topic and extract excerpts.

Usage:
  python scripts/libgen_fetch.py <topic> --top 5 --pages 30 --out topics/<dirname>
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

# Make `libgen` importable when this file is run directly.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from libgen.download import new_session, try_mirrors  # noqa: E402
from libgen.extract import write_excerpt  # noqa: E402
from libgen.metadata import RunMetadata, SourceRecord, now_iso, write_metadata  # noqa: E402
from libgen.search import search  # noqa: E402
from libgen.slug import dated_dirname, slugify  # noqa: E402


def resolve_out_dir(base: Path) -> Path:
    """If base exists, append _2, _3, ... until free."""
    if not base.exists():
        return base
    i = 2
    while True:
        candidate = base.with_name(f"{base.name}_{i}")
        if not candidate.exists():
            return candidate
        i += 1


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("topic", help="search topic")
    parser.add_argument("--top", type=int, default=5)
    parser.add_argument("--pages", type=int, default=30)
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="output dir; defaults to topics/YYYY-MM-DD_<slug>",
    )
    args = parser.parse_args(argv)

    out_dir = args.out or Path("topics") / dated_dirname(date.today().isoformat(), args.topic)
    out_dir = resolve_out_dir(out_dir)
    (out_dir / "sources").mkdir(parents=True, exist_ok=True)
    (out_dir / "summaries").mkdir(parents=True, exist_ok=True)

    print(f"[1/4] searching libgen for: {args.topic!r}")
    try:
        results = search(args.topic)
    except Exception as e:
        print(f"ERROR: search failed: {e}", file=sys.stderr)
        return 1

    # Filter: pdf/epub only, sort by year desc (None last), take top N
    filtered = [r for r in results if r.extension.lower() in {"pdf", "epub"}]
    filtered.sort(key=lambda r: (r.year or 0), reverse=True)
    chosen = filtered[: args.top]

    if not chosen:
        print("no PDF/EPUB results found for this topic", file=sys.stderr)
        return 2

    print(f"[2/4] found {len(chosen)} candidates, downloading...")
    session = new_session()
    meta = RunMetadata(topic=args.topic, fetched_at=now_iso(), out_dir=str(out_dir))

    for i, r in enumerate(chosen, start=1):
        sid = f"{i:02d}"
        slug = slugify(r.title)[:60] or f"book-{sid}"
        local = out_dir / "sources" / f"{sid}_{slug}.{r.extension.lower()}"
        excerpt = out_dir / "sources" / f"{sid}_{slug}_excerpt.txt"

        rec = SourceRecord(
            id=sid,
            title=r.title,
            authors=r.authors,
            year=r.year,
            pages=r.pages,
            extension=r.extension.lower(),
            md5=r.md5,
            libgen_mirrors=r.mirror_urls,
            local_path=str(local.relative_to(out_dir)),
            excerpt_path=str(excerpt.relative_to(out_dir)),
        )

        ok = try_mirrors(r.mirror_urls, local, session=session)
        if not ok:
            rec.status = "download_failed"
            rec.note = "all mirrors failed"
            meta.sources.append(rec)
            print(f"  [{sid}] FAIL download: {r.title[:60]}")
            continue

        print(f"[3/4] extracting excerpt for {sid}...")
        try:
            if r.extension.lower() == "pdf":
                write_excerpt(
                    local,
                    excerpt,
                    max_pages=args.pages,
                    metadata_header={
                        "Title": r.title,
                        "Authors": ", ".join(r.authors),
                        "Year": r.year or "",
                    },
                )
                rec.status = "ok"
            else:
                # EPUB: skip text extraction, just note it
                excerpt.write_text(
                    f"=== METADATA ===\nTitle: {r.title}\nExtension: {r.extension}\n"
                    "(EPUB excerpt extraction not supported in v1)\n",
                    encoding="utf-8",
                )
                rec.status = "ok"
                rec.note = "epub: no text extracted"
        except Exception as e:
            rec.status = "extract_failed"
            rec.note = str(e)[:200]
            print(f"  [{sid}] FAIL extract: {e}")

        meta.sources.append(rec)

    write_metadata(meta, out_dir / "metadata.json")
    ok_count = sum(1 for s in meta.sources if s.status == "ok")
    print(f"[4/4] done. {ok_count}/{len(meta.sources)} sources ready")
    print(f"output: {out_dir}")

    if ok_count < 2:
        print("ERROR: fewer than 2 sources succeeded", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

- [ ] **Step 2: Verify CLI help runs**

Run: `python scripts/libgen_fetch.py --help`
Expected: usage text printed.

- [ ] **Step 3: Dry-run end-to-end with a common topic**

Run: `python scripts/libgen_fetch.py "python programming" --top 2 --pages 5`

Expected:
- Creates `topics/<date>_python-programming/`
- Downloads at least one PDF into `sources/`
- Writes `metadata.json` with at least one `status: ok` entry
- Exits 0 if at least 2 succeed (otherwise 1 — acceptable for smoke check, inspect metadata.json to debug)

If the run fails due to parser column indices, return to Task 4 Step 4 and adjust.

- [ ] **Step 4: Commit**

```bash
git add scripts/libgen_fetch.py
git commit -m "feat: libgen_fetch CLI orchestration"
```

---

## Task 9: Slash command `/research`

**Files:**
- Create: `.claude/commands/research.md`

- [ ] **Step 1: Write the slash command**

`.claude/commands/research.md`:
```markdown
---
description: Research a topic by fetching top libgen books and synthesizing idea.md
---

You are executing a research workflow for the user. The topic is: **$ARGUMENTS**

Follow these steps exactly. Do not skip verification.

## Step 1 — Run the fetcher

Compute today's date in `YYYY-MM-DD` format. Run:

```bash
python scripts/libgen_fetch.py "$ARGUMENTS" --top 5 --pages 30
```

Read the last line of stdout to learn the output directory. If the exit code
is non-zero:
- Exit 2 → tell the user no results were found and ask them to broaden or
  rephrase the topic. Stop.
- Exit 1 → tell the user the fetch partially failed, show the error, and
  stop.

## Step 2 — Read metadata

Read `<out_dir>/metadata.json`. Collect the list of sources where
`status == "ok"`. If fewer than 2, stop and report to the user.

## Step 3 — Per-book summaries

For each OK source, read its `excerpt_path` and write
`<out_dir>/summaries/<id>_<slug>.md` using this template:

```markdown
# <Title>

**Author(s):** ...
**Year:** ...
**Source ID:** NN
**Excerpt basis:** TOC + first 30 pages  (or: TOC only, if the excerpt lacks page text)

## Thesis
2–3 sentences stating the main argument visible from the excerpt.

## Key concepts
- bullet
- bullet

## Methodology / framework
How the author approaches the topic.

## Notable passages
> quoted line from the excerpt
— approximate page if known

## Relevance to "<topic>"
Why this source matters for the current research question.
```

**Discipline:** Every claim in the summary must be grounded in the excerpt
text. If the excerpt only contains a TOC (no page text), say so explicitly
and keep the summary correspondingly shallow. Do not invent content.

## Step 4 — Synthesize `idea.md`

Read every summary you just wrote. Produce `<out_dir>/idea.md`:

```markdown
# Research notes: <topic>

**Generated:** YYYY-MM-DD
**Sources used:** N of M

## 1. Topic & scope
What the user asked for, any implicit scoping decisions.

## 2. Sources
1. Title — Author(s), Year
2. ...

## 3. Key themes
Cross-source patterns. Every claim must cite `[Source NN]` — at least one
per claim. Flag disagreements between sources explicitly.

## 4. Research ideas
Concrete angles for a research project: questions, methodologies,
comparisons. Each idea grounded in cited sources.

## 5. Gaps & open questions
What the excerpts did not cover and what would need additional sources.

## 6. References
Full list with title, author(s), year, and the first libgen_mirror URL
from metadata.json.
```

**Discipline:** No fabrication. If a theme only appears in one source, say
so. If the excerpts were thin, section 5 should be longer than section 3.

## Step 5 — Report

Tell the user:
- The path to `idea.md`
- Number of sources used vs attempted
- Any sources that failed and why (from metadata.json)
```

- [ ] **Step 2: Commit**

```bash
git add .claude/commands/research.md
git commit -m "feat: /research slash command"
```

---

## Task 10: End-to-end smoke test

**Files:** none created — this is verification.

- [ ] **Step 1: Run the full workflow**

In Claude Code, run: `/research "python programming"`

- [ ] **Step 2: Verify artifacts**

Check that the newest `topics/<date>_python-programming*/` directory contains:
- `metadata.json` with at least 2 sources where `status == "ok"`
- `sources/` with downloaded PDFs and `_excerpt.txt` files
- `summaries/` with one markdown file per OK source
- `idea.md` with all 6 sections and at least one `[Source NN]` citation in sections 3 and 4

Run:
```bash
ls topics/*/idea.md | tail -1 | xargs grep -c '\[Source'
```
Expected: number > 0.

- [ ] **Step 3: Verify fail-soft**

Manually edit `metadata.json` in a test run to mark one source as
`download_failed`, re-run only Steps 2–5 of the slash command mentally (or
run `/research` on a rare topic that yields limited results) and confirm
Claude still produces `idea.md` using the remaining sources.

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "test: end-to-end smoke test passing" --allow-empty
```

---

## Spec Coverage Check

| Spec section | Implemented in |
|---|---|
| Slash command trigger | Task 9 |
| `libgen_fetch.py` CLI interface | Task 8 |
| Search + parse libgen.vg | Tasks 3, 4 |
| Mirror resolve + download | Task 5 |
| PDF TOC + first-M-pages extract | Task 6 |
| `metadata.json` schema | Task 7 |
| Fail-soft (status per source, ≥2 required) | Task 8 |
| Slugify + non-ASCII topics | Task 2 |
| Retry with backoff on network errors | Task 4 (`search`), Task 5 (`try_mirrors`) |
| Re-run same topic same day → suffix | Task 8 (`resolve_out_dir`) |
| Per-book summary template | Task 9 |
| `idea.md` 6-section template | Task 9 |
| Citation discipline `[Source NN]` | Task 9 + Task 10 verification |
| Unit tests (slugify, parser) | Tasks 2, 4 |
| Integration/smoke test | Task 10 |
