# Libgen Research Workflow — Design Spec

**Date:** 2026-04-06
**Status:** Approved, ready for implementation plan

## Goal

Build a one-command research workflow that, given a topic, pulls relevant books
from libgen.vg, extracts key excerpts, and produces a synthesized ideas document
(`idea.md`) for use as a starting point for academic/research work.

The workflow splits responsibilities cleanly:

- **Python** handles deterministic work: HTTP, HTML parsing, PDF download, text
  extraction.
- **Claude Code** handles reasoning: reading excerpts, summarizing per-book,
  synthesizing cross-source themes and research ideas.

## Trigger

Slash command in Claude Code:

```
/research "hunt"
/research "artificial intelligence ethics"
```

The command is defined in `.claude/commands/research.md` and expands into a
prompt that orchestrates the full pipeline.

## Architecture

```
User: /research "<topic>"
  │
  ▼
.claude/commands/research.md      (slash command prompt)
  │
  ▼
Claude Code orchestrates:
  1. Bash → scripts/libgen_fetch.py "<topic>" --top 5 --pages 30 --out topics/<date>_<slug>
  2. Read topics/<date>_<slug>/metadata.json
  3. For each successful source:
       Read sources/NN_<slug>_excerpt.txt
       Write summaries/NN_<slug>.md
  4. Read all summaries → synthesize → write idea.md
  5. Report result path to user
```

## Folder Structure

```
research/
├── .claude/
│   └── commands/
│       └── research.md
├── scripts/
│   ├── libgen_fetch.py
│   └── requirements.txt
├── docs/
│   └── superpowers/
│       └── specs/
│           └── 2026-04-06-libgen-research-workflow-design.md
└── topics/
    └── YYYY-MM-DD_<slug>/
        ├── metadata.json
        ├── sources/
        │   ├── 01_<slug>.pdf
        │   ├── 01_<slug>_excerpt.txt
        │   └── ...
        ├── summaries/
        │   ├── 01_<slug>.md
        │   └── ...
        └── idea.md
```

## Component 1 — `scripts/libgen_fetch.py`

### Purpose
Fetch, download, and extract excerpts for top-N books matching a topic from
libgen.vg. Produce a deterministic artifact layout that Claude can consume.

### Interface
```
python scripts/libgen_fetch.py <topic> \
    --top 5 \
    --pages 30 \
    --out topics/<date>_<slug>
```

Arguments:
- `topic` (positional, required): search string. May contain spaces and
  non-ASCII; will be URL-encoded.
- `--top N` (default 5): number of books to download.
- `--pages M` (default 30): number of leading pages to extract as excerpt.
- `--out PATH` (required): output directory for this run.

Exit codes:
- `0`: success, at least 2 of N books processed successfully.
- `2`: zero results from libgen search.
- `1`: other errors (network, all downloads failed, etc).

### Steps
1. **Search.** GET `https://libgen.vg/index.php?req=<urlencoded topic>&...`
   with the same columns/objects/topics filters as the reference URL. Parse
   result rows with BeautifulSoup.
2. **Filter & rank.** Keep only rows with extension `pdf` or `epub`. Sort by
   year descending (fallback: leave original order). Take top N.
3. **Resolve download.** For each selected row, follow mirror link and resolve
   the direct download URL (libgen.vg typically proxies through `books.ms` or
   `library.lol`). Download to `sources/NN_<slug>.<ext>` with a progress bar.
4. **Extract text.** Use `pypdf` to:
   - Read the document outline / table of contents if present.
   - Extract text from the first M pages.
   - Concatenate into `sources/NN_<slug>_excerpt.txt` with clear section
     markers:
     ```
     === METADATA ===
     Title: ...
     Author: ...
     Year: ...

     === TABLE OF CONTENTS ===
     ...

     === FIRST <M> PAGES ===
     ...
     ```
5. **Write metadata.** Save `metadata.json` with an array of entries:
   ```json
   {
     "topic": "hunt",
     "fetched_at": "2026-04-06T12:34:56Z",
     "sources": [
       {
         "id": "01",
         "title": "...",
         "authors": ["..."],
         "year": 2019,
         "pages": 412,
         "extension": "pdf",
         "md5": "...",
         "libgen_url": "...",
         "local_path": "sources/01_<slug>.pdf",
         "excerpt_path": "sources/01_<slug>_excerpt.txt",
         "status": "ok" | "download_failed" | "extract_failed",
         "note": "optional error detail"
       }
     ]
   }
   ```

### Fail-soft behavior
- Any individual book that fails to download or extract is marked with a
  `status` other than `ok` and the pipeline continues.
- If fewer than 2 books succeed, exit with code 1 so Claude can tell the user
  to retry or broaden the topic.

### Dependencies (`scripts/requirements.txt`)
```
requests>=2.31
beautifulsoup4>=4.12
pypdf>=4.0
tqdm>=4.66
```

### Edge cases
- **Non-ASCII topics.** URL-encode the query string. Slugify folder names by
  stripping diacritics and replacing whitespace with `-`.
- **Rate limiting / transient 5xx.** Retry 3x with exponential backoff (1s,
  2s, 4s) on network errors.
- **Corrupt PDFs.** Catch `pypdf` exceptions, mark status, continue.
- **Re-run same topic same day.** If output dir already exists, append
  `_2`, `_3`, ... to the directory name.

## Component 2 — `.claude/commands/research.md`

### Purpose
Slash command that expands into an orchestration prompt for Claude Code.

### Behavior (prompt pseudocode)
```
You are executing a research workflow. The user topic is: $ARGUMENTS

1. Compute today's date (YYYY-MM-DD) and a slug from the topic.
   Output directory: topics/<date>_<slug>
   If it already exists, append _2, _3, ...

2. Run:
   python scripts/libgen_fetch.py "<topic>" --top 5 --pages 30 --out <outdir>

   If exit code != 0, report the error to the user and stop.

3. Read <outdir>/metadata.json. For each entry with status == "ok":
   a. Read the excerpt file.
   b. Write <outdir>/summaries/NN_<slug>.md using the per-book summary
      template below. Only claims that are supported by the excerpt are
      allowed. If the excerpt is thin (TOC-only), say so explicitly.

4. Read all summary files. Synthesize idea.md at <outdir>/idea.md using the
   synthesis template below.

5. Report to the user: path to idea.md and number of sources used.
```

### Per-book summary template
```markdown
# <Title>

**Author(s):** ...
**Year:** ...
**Source ID:** NN
**Excerpt basis:** TOC + first M pages  (or: TOC only)

## Thesis
2-3 sentences stating the main argument of the book as visible from the excerpt.

## Key concepts
- ...
- ...

## Methodology / framework
How the author approaches the topic.

## Notable passages
> quote
— context / approximate page

## Relevance to "<topic>"
Why this source matters for the current research question.
```

### Synthesis template — `idea.md`
```markdown
# Research notes: <topic>

**Generated:** YYYY-MM-DD
**Sources used:** N of M

## 1. Topic & scope
What the user asked for, any implicit scoping decisions made.

## 2. Sources
Numbered list of books actually read, with title, author, year.

## 3. Key themes
Cross-source patterns. Every claim must cite at least one source as
`[Source NN]`. Flag disagreements between sources.

## 4. Research ideas
Concrete angles for a research project — questions to investigate,
methodologies that could be applied, comparisons worth making. Each idea
grounded in the sources.

## 5. Gaps & open questions
What the excerpts did not cover, what seems under-explored, what would
require additional sources.

## 6. References
Full bibliographic list (title, author, year, and libgen URL from
metadata.json).
```

### Citation discipline
Claude MUST NOT fabricate claims that are not supported by the excerpts. If
the excerpt is thin (e.g., TOC only, extraction partial), the summary and
synthesis must say so rather than inventing detail.

## Error Handling Summary

| Failure | Behavior |
|---|---|
| libgen search returns 0 results | Script exit 2, Claude asks user to broaden/rephrase |
| libgen unreachable / 5xx | Retry 3x with backoff, then exit 1 |
| Individual PDF download fails | Mark status, continue with others |
| PDF extraction fails | Mark status, continue with others |
| Fewer than 2 books succeed | Exit 1, Claude reports partial failure |
| Output dir already exists | Append numeric suffix |
| Non-ASCII topic | URL-encode for query, slugify for folder |

## Testing Plan

1. **Unit:** parser tests using a saved HTML fixture of a libgen search
   result page. Verifies row extraction, filter, rank.
2. **Unit:** slugify tests (ASCII, diacritics, punctuation).
3. **Integration (manual):** run `/research "python"` end-to-end. Verify
   `idea.md` contains all 6 sections and every claim in sections 3 and 4
   carries a `[Source NN]` citation.
4. **Smoke:** verify fail-soft — artificially break one download URL,
   confirm the rest of the pipeline still produces `idea.md`.

## Out of Scope

- Full-book summarization (only first N pages + TOC).
- Non-PDF/EPUB formats.
- Automatic topic expansion or multi-query search.
- Caching / deduplication across runs.
- A UI beyond the slash command.
