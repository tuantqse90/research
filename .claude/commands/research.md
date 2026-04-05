---
description: Research a topic by fetching top libgen books and synthesizing idea.md
---

You are executing a research workflow for the user. The topic is: **$ARGUMENTS**

Follow these steps exactly. Do not skip verification.

## Step 0 — Verify tor proxy is running

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

Activate the venv and run the fetcher through the tor proxy:

```bash
source .venv/bin/activate && \
  HTTPS_PROXY=socks5h://127.0.0.1:9050 \
  HTTP_PROXY=socks5h://127.0.0.1:9050 \
  ALL_PROXY=socks5h://127.0.0.1:9050 \
  python scripts/libgen_fetch.py "$ARGUMENTS" --top 5 --pages 30
```

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

## Step 5 — Report

Tell the user:
- The path to `idea.md`
- Number of sources used vs attempted
- Any sources that failed and why (from metadata.json)
