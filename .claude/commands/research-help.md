---
description: Show usage and options for the /research command
---

Display the following help text to the user exactly as-is (do NOT run any tools):

```
/research <topic> [options]

Search libgen, arXiv, and IACR ePrint for papers on a topic,
download PDFs, extract excerpts, and generate idea.md + research.md.

OPTIONS
  --top N          Max results per source (default: 5)
  --sources S      Comma-separated sources: all, libgen, arxiv, iacr (default: all)

SHORTCUTS
  --libgen         Same as --sources libgen
  --arxiv          Same as --sources arxiv
  --iacr           Same as --sources iacr
  (combine: --arxiv --iacr = --sources arxiv,iacr)

EXAMPLES
  /research zero knowledge proof
      → all sources, 5 per source (up to 15 papers)

  /research zero knowledge proof --top 3
      → all sources, 3 per source (up to 9 papers)

  /research zk-SNARK --arxiv
      → arXiv only, 5 papers, no Tor needed

  /research zk-SNARK --arxiv --iacr --top 10
      → arXiv + IACR, 10 per source (up to 20 papers), no Tor needed

  /research recommender systems --libgen
      → libgen only, 5 papers, requires Tor

SOURCES
  libgen    Books and journal articles (requires Tor proxy at 127.0.0.1:9050)
  arxiv     Preprints (direct access, fast)
  iacr      Cryptography papers from IACR ePrint (direct access, fast)

OUTPUT (in topics/YYYY-MM-DD_<slug>/)
  sources/        Downloaded PDFs + extracted excerpts
  summaries/      Per-source summaries
  metadata.json   Run metadata and per-source status
  idea.md         Cross-source synthesis
  research.md     Comparative analysis (gaps, contradictions, opportunities)

OTHER COMMANDS
  /research-help  This help text
```
