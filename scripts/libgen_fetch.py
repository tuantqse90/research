#!/usr/bin/env python3
"""Fetch top-N papers/books from libgen, arXiv, and IACR ePrint for a topic.

Usage:
  python scripts/libgen_fetch.py <topic> [--top 5] [--pages 30] [--sources all]

Source selection:
  --sources all      Search all sources (default)
  --sources libgen   Search libgen only
  --sources arxiv    Search arXiv only
  --sources iacr     Search IACR ePrint only
  --sources arxiv,iacr  Comma-separated combination
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

# Make `libgen` importable when this file is run directly.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from libgen.arxiv import search_arxiv  # noqa: E402
from libgen.download import download_file, new_session, try_mirrors  # noqa: E402
from libgen.extract import write_excerpt  # noqa: E402
from libgen.iacr import search_iacr  # noqa: E402
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
    parser.add_argument("--top", type=int, default=5, help="max results per source (default: 5)")
    parser.add_argument("--pages", type=int, default=30)
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="output dir; defaults to topics/YYYY-MM-DD_<slug>",
    )
    parser.add_argument(
        "--sources",
        default="all",
        help="comma-separated list of sources: all, libgen, arxiv, iacr (default: all)",
    )
    args = parser.parse_args(argv)

    # Parse source selection
    if args.sources.strip().lower() == "all":
        enabled_sources = {"libgen", "arxiv", "iacr"}
    else:
        enabled_sources = {s.strip().lower() for s in args.sources.split(",")}
        valid = {"libgen", "arxiv", "iacr"}
        unknown = enabled_sources - valid
        if unknown:
            print(f"ERROR: unknown sources: {unknown}. Valid: {valid}", file=sys.stderr)
            return 1

    out_dir = args.out or Path("topics") / dated_dirname(date.today().isoformat(), args.topic)
    out_dir = resolve_out_dir(out_dir)
    (out_dir / "sources").mkdir(parents=True, exist_ok=True)
    (out_dir / "summaries").mkdir(parents=True, exist_ok=True)

    all_results = []
    src_label = ", ".join(sorted(enabled_sources))

    # --- Search libgen ---
    if "libgen" in enabled_sources:
        print(f"[1/4] searching libgen for: {args.topic!r}")
        try:
            libgen_results = search(args.topic)
            libgen_pdf = [r for r in libgen_results if r.extension.lower() in {"pdf", "epub"}]
            libgen_pdf.sort(key=lambda r: (r.year or 0), reverse=True)
            all_results.extend(("libgen", r) for r in libgen_pdf[:args.top])
            print(f"       libgen: {len(libgen_pdf)} found, taking top {min(len(libgen_pdf), args.top)}")
        except Exception as e:
            print(f"       libgen: search failed ({e})")

    # --- Search arXiv (no tor needed) ---
    if "arxiv" in enabled_sources:
        print(f"[1/4] searching arXiv for: {args.topic!r}")
        try:
            arxiv_session = new_session()
            arxiv_results = search_arxiv(args.topic, max_results=args.top, session=arxiv_session)
            all_results.extend(("arxiv", r) for r in arxiv_results)
            print(f"       arXiv:  {len(arxiv_results)} found")
        except Exception as e:
            print(f"       arXiv:  search failed ({e})")

    # --- Search IACR ePrint (no tor needed) ---
    if "iacr" in enabled_sources:
        print(f"[1/4] searching IACR ePrint for: {args.topic!r}")
        try:
            iacr_session = new_session()
            iacr_results = search_iacr(args.topic, max_results=args.top, session=iacr_session)
            all_results.extend(("iacr", r) for r in iacr_results)
            print(f"       IACR:   {len(iacr_results)} found")
        except Exception as e:
            print(f"       IACR:   search failed ({e})")

    # Deduplicate by title similarity, keep all (each source already capped at --top)
    chosen = _dedupe(all_results)

    if not chosen:
        print("no PDF/EPUB results found for this topic", file=sys.stderr)
        return 2

    print(f"[2/4] selected {len(chosen)} candidates, downloading...")
    session = new_session()
    meta = RunMetadata(topic=args.topic, fetched_at=now_iso(), out_dir=str(out_dir))

    for i, (source_name, r) in enumerate(chosen, start=1):
        sid = f"{i:02d}"
        slug = slugify(r.title)[:60] or f"paper-{sid}"
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
        rec.note = f"source: {source_name}"

        # Download: arXiv/IACR have direct PDF links, libgen needs mirror resolution
        ok = False
        if source_name in ("arxiv", "iacr"):
            # Direct PDF download, no mirror resolution needed
            for url in r.mirror_urls:
                ok = download_file(url, local, session=session)
                if ok:
                    break
        else:
            ok = try_mirrors(r.mirror_urls, local, session=session)

        if not ok:
            rec.status = "download_failed"
            rec.note += "; all mirrors failed"
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
                excerpt.write_text(
                    f"=== METADATA ===\nTitle: {r.title}\nExtension: {r.extension}\n"
                    "(EPUB excerpt extraction not supported in v1)\n",
                    encoding="utf-8",
                )
                rec.status = "ok"
                rec.note += "; epub: no text extracted"
        except Exception as e:
            rec.status = "extract_failed"
            rec.note += f"; {str(e)[:200]}"
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


def _dedupe(
    tagged_results: list[tuple[str, object]],
) -> list[tuple[str, object]]:
    """Deduplicate by normalized title. Each source already capped at --top."""
    seen_titles: set[str] = set()
    result = []

    for source_name, r in tagged_results:
        norm = slugify(r.title)[:40]
        if norm in seen_titles:
            continue
        seen_titles.add(norm)
        result.append((source_name, r))

    return result


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
