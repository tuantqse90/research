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
