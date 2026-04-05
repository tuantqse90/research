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
