---
description: Research a topic by fetching from libgen + arXiv + IACR ePrint, synthesizing idea.md and comparative research.md
---

You are executing a research workflow for the user.

Parse `$ARGUMENTS` to extract:
- **topic**: the search query (required)
- **--topN**: number of results (optional, default 10), e.g. `--top5` or `--top 15`
- **--sources**: source filter (optional, default `all`), e.g. `--libgen`, `--arxiv`, `--iacr`, or `--sources arxiv,iacr`

Shorthand: `--libgen` means `--sources libgen`, `--arxiv` means `--sources arxiv`,
`--iacr` means `--sources iacr`. Multiple can be combined: `--arxiv --iacr` means
`--sources arxiv,iacr`.

Examples:
- `/research zero knowledge proof` → topic="zero knowledge proof", top=10, sources=all
- `/research zero knowledge proof --top5` → topic="zero knowledge proof", top=5, sources=all
- `/research zero knowledge proof --libgen` → topic="zero knowledge proof", top=10, sources=libgen
- `/research zk-SNARK --arxiv --iacr --top15` → topic="zk-SNARK", top=15, sources=arxiv,iacr

Follow these steps exactly. Do not skip verification.

## Step 0 — Verify tor proxy is running

**Skip this step if `--sources` does not include `libgen`** (arXiv and IACR
don't need tor).

libgen.vg is blocked from this network and must be accessed through the local
tor SOCKS5 proxy at `127.0.0.1:9050`. Check it:

```bash
curl -s --socks5-hostname 127.0.0.1:9050 --max-time 10 https://check.torproject.org/api/ip
```

Expected output contains `"IsTor":true`. If it fails or times out, tell the
user:

> Tor proxy is not reachable at 127.0.0.1:9050. Start it with:
> `/opt/homebrew/opt/tor/bin/tor --quiet &`
> Then re-run `/research "$ARGUMENTS"`.

Stop if the proxy check fails.

## Step 1 — Run the fetcher

The fetcher searches up to three sources: **libgen** (books/journals, via tor),
**arXiv** (preprints, direct), and **IACR ePrint** (cryptography, direct).
Results are interleaved and deduplicated.

Activate the venv and run the fetcher. Use the parsed top/sources values:

```bash
source .venv/bin/activate && \
  HTTPS_PROXY=socks5h://127.0.0.1:9050 \
  HTTP_PROXY=socks5h://127.0.0.1:9050 \
  ALL_PROXY=socks5h://127.0.0.1:9050 \
  python scripts/libgen_fetch.py "<topic>" --top <N> --sources <sources> --pages 30
```

Replace `<topic>`, `<N>`, `<sources>` with the parsed values. If sources is
`all`, use `--sources all`. If only arxiv+iacr, use `--sources arxiv,iacr`.

Read the last line of stdout to learn the output directory (format:
`output: topics/YYYY-MM-DD_<slug>`). If the exit code is non-zero:
- Exit 2 → tell the user no results were found and ask them to broaden or
  rephrase the topic. Stop.
- Exit 1 → tell the user the fetch partially failed, show the error, and
  stop.

## Step 2 — Read metadata

Read `<out_dir>/metadata.json`. Collect the list of sources where
`status == "ok"`. If fewer than 2, stop and report to the user.

## Step 3 — Per-book summaries

For each OK source, read its `excerpt_path` (resolve relative to `<out_dir>`)
and write `<out_dir>/summaries/<id>_<slug>.md` using this template:

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

## Step 5 — Comparative analysis `research.md`

Read every summary you just wrote AND `idea.md`. Produce `<out_dir>/research.md`:

```markdown
# Comparative analysis: <topic>

**Generated:** YYYY-MM-DD
**Sources analyzed:** N of M

## 1. Sources overview
| # | Title | Author(s) | Year | Approach |
|---|-------|-----------|------|----------|
| 1 | ...   | ...       | ...  | ...      |

## 2. Methodological differences
How each source approaches the problem differently. Compare frameworks,
algorithms, datasets, evaluation metrics. Every claim must cite
`[Source NN]`.

## 3. Contradictions & disagreements
Where sources explicitly or implicitly contradict each other. State each
side clearly with citations. If no contradictions exist, say so honestly.

## 4. Unique contributions
What each source brings that no other source covers. One subsection per
source — if a source adds nothing unique, state that.

## 5. Convergence points
Where multiple sources agree or reinforce each other. These represent
stronger evidence. Cite all agreeing sources.

## 6. Gaps in the literature
What none of the sources address. Missing perspectives, unstudied
variables, under-represented domains, methodological blind spots.
This is the most valuable section — be thorough.

## 7. Research opportunities
Concrete research directions that arise from the gaps and contradictions
identified above. Each opportunity must reference specific gaps or
disagreements from sections 3, 4, or 6.

## 8. References
Full list with title, author(s), year, and the first libgen_mirror URL
from metadata.json.
```

**Discipline:** No fabrication. Every comparison must be grounded in the
excerpts. If an excerpt was thin (TOC only), mark that source's claims as
low-confidence. Gaps (section 6) should be the longest section — that is
where the real value lies.

## Step 6 — Report

Tell the user:
- The path to `idea.md` and `research.md`
- Number of sources used vs attempted
- Any sources that failed and why (from metadata.json)
