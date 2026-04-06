<p align="center">
  <h1 align="center">research</h1>
  <p align="center">
    Automated research assistant powered by Claude Code.<br/>
    Search &bull; Download &bull; Extract &bull; Summarize &bull; Analyze
  </p>
</p>

<p align="center">
  <a href="#features">Features</a> &bull;
  <a href="#quick-start">Quick Start</a> &bull;
  <a href="#usage">Usage</a> &bull;
  <a href="#sources">Sources</a> &bull;
  <a href="#output">Output</a> &bull;
  <a href="#project-structure">Project Structure</a>
</p>

---

## Overview

A CLI tool and [Claude Code](https://claude.ai/claude-code) slash command that searches multiple academic sources for papers on a given topic, downloads PDFs, extracts excerpts (TOC + first N pages), and generates:

- **Per-source summaries** grounded in excerpt text
- **`idea.md`** cross-source synthesis with research ideas
- **`research.md`** comparative analysis with gaps, contradictions, and opportunities

## Features

| Feature | Description |
|---------|-------------|
| **Multi-source search** | libgen.vg, arXiv, IACR ePrint in a single command |
| **Source filtering** | `--sources arxiv,iacr` or shortcuts `--arxiv`, `--libgen` |
| **Per-source top N** | `--top 5` means 5 results from *each* enabled source |
| **Auto-deduplication** | Removes duplicate papers across sources |
| **Tor integration** | libgen access via SOCKS5 proxy; arXiv/IACR direct |
| **PDF extraction** | TOC + first N pages via pypdf |
| **Mirror retry** | Automatic mirror resolution with fresh keys on failure |
| **Slash commands** | `/research <topic>` and `/research-help` in Claude Code |

## Quick Start

```bash
# 1. Clone and setup
git clone https://github.com/tuantqse90/research.git
cd research
python -m venv .venv
source .venv/bin/activate
pip install -r scripts/requirements.txt

# 2. Start Tor proxy (needed for libgen only)
/opt/homebrew/opt/tor/bin/tor --quiet &

# 3. Run
python scripts/libgen_fetch.py "zero knowledge proof" --top 5 --pages 30
```

## Requirements

| Requirement | Notes |
|-------------|-------|
| Python 3.12+ | |
| Tor proxy | `127.0.0.1:9050` — only needed for libgen source |
| pip packages | `requests[socks]`, `beautifulsoup4`, `pypdf`, `tqdm`, `pytest` |

## Usage

### CLI

```bash
python scripts/libgen_fetch.py <topic> [options]
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--top N` | `5` | Max results **per source** |
| `--pages N` | `30` | Max pages to extract from each PDF |
| `--sources S` | `all` | Comma-separated: `all`, `libgen`, `arxiv`, `iacr` |
| `--out PATH` | auto | Output directory (default: `topics/YYYY-MM-DD_<slug>`) |

**Shortcuts:**

| Shortcut | Equivalent |
|----------|------------|
| `--libgen` | `--sources libgen` |
| `--arxiv` | `--sources arxiv` |
| `--iacr` | `--sources iacr` |

**Examples:**

```bash
# All sources, 5 per source (up to 15 papers)
python scripts/libgen_fetch.py "zero knowledge proof" --top 5

# arXiv only, no Tor needed
python scripts/libgen_fetch.py "transformer architecture" --sources arxiv

# arXiv + IACR, 10 per source
python scripts/libgen_fetch.py "zk-SNARK" --sources arxiv,iacr --top 10

# libgen only, requires Tor
HTTPS_PROXY=socks5h://127.0.0.1:9050 \
  python scripts/libgen_fetch.py "recommender systems" --sources libgen
```

### Claude Code

```
/research zero knowledge proof
/research zk-SNARK --arxiv --iacr --top 10
/research recommender systems --libgen --top 3
/research-help
```

The `/research` command runs the full pipeline:
1. Search enabled sources
2. Download PDFs
3. Extract excerpts
4. Generate per-source summaries
5. Synthesize `idea.md`
6. Generate comparative `research.md`

## Sources

| Source | Access | Speed | Content |
|--------|--------|-------|---------|
| [libgen.vg](https://libgen.vg) | Via Tor proxy | Slow (~40 KB/s) | Books, journal articles |
| [arXiv](https://arxiv.org) | Direct | Fast | Preprints, all fields |
| [IACR ePrint](https://eprint.iacr.org) | Direct | Fast | Cryptography papers |

## Output

Each run creates a directory at `topics/YYYY-MM-DD_<slug>/`:

```
topics/2026-04-06_zero-knowledge-proof/
  metadata.json           # Run metadata, per-source status
  idea.md                 # Cross-source synthesis
  research.md             # Comparative analysis
  sources/
    01_paper-slug.pdf          # Downloaded PDF
    01_paper-slug_excerpt.txt  # Extracted text (TOC + pages)
    02_paper-slug.pdf
    02_paper-slug_excerpt.txt
    ...
  summaries/
    01_paper-slug.md           # Per-source summary
    02_paper-slug.md
    ...
```

### `idea.md` — Synthesis

Cross-source research notes: topic scope, key themes, research ideas, gaps, and references. Every claim cites `[Source NN]`.

### `research.md` — Comparative Analysis

Deep comparison across sources: methodological differences, contradictions, unique contributions, convergence points, literature gaps, and research opportunities. The gaps section is the most valuable.

## Tests

```bash
pytest tests/ -v
```

## Project Structure

```
.claude/commands/
  research.md             # /research slash command definition
  research-help.md        # /research-help slash command

scripts/
  libgen_fetch.py         # CLI entry point (multi-source orchestrator)
  requirements.txt        # Python dependencies
  libgen/
    __init__.py
    search.py             # libgen.vg HTML search parser
    arxiv.py              # arXiv API search (Atom XML)
    iacr.py               # IACR ePrint HTML search parser
    download.py           # Mirror resolver and PDF downloader
    extract.py            # PDF TOC and page text extractor
    metadata.py           # Run metadata and JSON writer
    slug.py               # Topic slug utilities

tests/
  __init__.py
  fixtures/               # HTML fixtures for parser tests
  test_search_parser.py   # libgen search HTML parsing tests
  test_slug.py            # Slug generation tests

topics/                   # Research output (git-ignored per topic)

.github/workflows/
  ci.yml                  # GitHub Actions: pytest on Python 3.12/3.13
```

## Workflow Diagram

```
                    /research "topic" --top 5
                              |
                    +---------+---------+
                    |         |         |
                 libgen     arXiv    IACR
                 (tor)    (direct)  (direct)
                    |         |         |
                    +----+----+----+----+
                         |         |
                    deduplicate    |
                         |         |
                    download PDFs  |
                         |         |
                    extract excerpts
                         |
              +----------+----------+
              |          |          |
          summaries   idea.md   research.md
```

## License

Private.

---

<p align="center">
  Built with <a href="https://claude.ai/claude-code">Claude Code</a>
</p>
