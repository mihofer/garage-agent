#!/usr/bin/env python3
"""Import forum threads into the garage-knowledge archive index.

Input: JSONL, one thread per line:
  {"url": "...", "title": "...", "author": "...", "date": "2024-03-01",
   "body": "problem ... solution ..."}

Re-importing the same URL replaces the previous entry.

Usage:
  python -m ingest.import_archive threads.jsonl [more.jsonl ...]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp_server import knowledge  # noqa: E402


def import_jsonl(paths: list[str]) -> tuple[int, int]:
    """Returns (added, skipped)."""
    con = knowledge.connect()
    added = skipped = 0
    try:
        for path in paths:
            with open(path, encoding="utf-8") as fh:
                for lineno, line in enumerate(fh, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                        assert rec.get("url") and rec.get("title") and rec.get("body")
                    except Exception as e:  # noqa: BLE001
                        print(f"  skip {path}:{lineno}: {e}")
                        skipped += 1
                        continue
                    knowledge.add_archive_entry(
                        con, rec["url"], rec["title"],
                        rec.get("author", ""), rec.get("date", ""), rec["body"])
                    added += 1
        con.commit()
    finally:
        con.close()
    return added, skipped


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    con = knowledge.connect()
    before = con.execute("SELECT COUNT(*) FROM archive").fetchone()[0]
    con.close()
    added, skipped = import_jsonl(sys.argv[1:])
    print(f"imported {added} threads ({skipped} skipped, archive now has {before + added})")


if __name__ == "__main__":
    main()
