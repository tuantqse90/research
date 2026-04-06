# research

Automated research assistant that searches [libgen.vg](https://libgen.vg) for books on a given topic, downloads PDFs, extracts excerpts (TOC + first N pages), and synthesizes per-book summaries into a unified `idea.md` research note.

## Features

- Search libgen.vg via Tor SOCKS5 proxy
- Download top-N books with automatic mirror resolution and retry
- Extract TOC and first pages from PDFs
- Generate per-book summaries and cross-source synthesis (`idea.md`)
- Claude Code `/research` slash command for end-to-end workflow

## Requirements

- Python 3.12+
- Tor proxy running on `127.0.0.1:9050`

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r scripts/requirements.txt
```

Start the Tor proxy:

```bash
/opt/homebrew/opt/tor/bin/tor --quiet &
```

## Usage

### CLI

```bash
source .venv/bin/activate
HTTPS_PROXY=socks5h://127.0.0.1:9050 \
  python scripts/libgen_fetch.py "recommender systems" --top 5 --pages 30
```

Output is written to `topics/YYYY-MM-DD_<slug>/` containing:
- `pdfs/` — downloaded PDFs
- `excerpts/` — extracted text (TOC + first pages)
- `metadata.json` — run metadata and per-source status

### Claude Code

```
/research recommender systems
```

This runs the full pipeline: fetch, summarize each book, and synthesize `idea.md`.

## Tests

```bash
pytest tests/ -v
```

## Project Structure

```
scripts/
  libgen_fetch.py       # CLI entry point
  libgen/
    search.py           # libgen.vg search parser
    download.py         # mirror resolver and file downloader
    extract.py          # PDF TOC and excerpt extractor
    metadata.py         # run metadata and JSON writer
    slug.py             # topic slug utilities
tests/
  test_search_parser.py # search HTML parsing tests
  test_slug.py          # slug generation tests
topics/                 # research output (per-topic directories)
```

## License

Private.
