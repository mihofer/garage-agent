#!/usr/bin/env python3
"""Build a static HTML timeline/gallery from the photo store (pure stdlib).

Photo store layout (managed by the docu skill):
  photos/YYYY/YYYY-MM-DD_job/IMG_0001.jpg      photo file
  photos/YYYY/YYYY-MM-DD_job/IMG_0001.json     sidecar: {"caption","job","note"}

Output: photos/index.html — grouped by month, newest first.

Usage: build_gallery.py [--photos-dir PATH] [--out index.html]
"""

from __future__ import annotations

import argparse
import html
import json
import os
from datetime import date
from pathlib import Path

IMG_EXT = {".jpg", ".jpeg", ".png", ".webp"}


def collect_entries(photos_dir: Path) -> list[dict]:
    entries = []
    for sidecar in sorted(photos_dir.rglob("*.json")):
        # convention: sidecar name = image filename + ".json" (IMG_1.jpg -> IMG_1.jpg.json)
        if not sidecar.name.endswith(".json") or sidecar.stem == sidecar.name:
            continue
        img = Path(str(sidecar)[:-len(".json")])
        if img.suffix.lower() not in IMG_EXT or not img.exists():
            continue
        try:
            meta = json.loads(sidecar.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            meta = {}
        rel = img.relative_to(photos_dir).as_posix()
        # day folder convention: YYYY-MM-DD[_job]
        folder = img.parent.name
        day = folder[:10] if len(folder) >= 10 and folder[4] == "-" else ""
        entries.append({
            "src": rel,
            "day": day,
            "job": meta.get("job", ""),
            "caption": meta.get("caption", "(no caption yet)"),
            "note": meta.get("note", ""),
        })
    return sorted(entries, key=lambda e: (e["day"], e["src"]), reverse=True)


def render(entries: list[dict], title: str) -> str:
    months: dict[str, list[dict]] = {}
    for e in entries:
        months.setdefault(e["day"][:7] or "unknown", []).append(e)

    parts = [f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>
 body {{ font-family: system-ui, sans-serif; max-width: 1100px; margin: 0 auto; padding: 1rem; }}
 h1 {{ font-size: 1.4rem; }} h2 {{ border-bottom: 2px solid #ccc; padding-bottom: .2rem; }}
 .card {{ display:inline-block; width:300px; margin:.5rem; vertical-align:top;
          border:1px solid #ddd; border-radius:8px; overflow:hidden; }}
 .card img {{ width:100%; height:200px; object-fit:cover; display:block; }}
 .card .cap {{ padding:.5rem; font-size:.85rem; }}
 .card .meta {{ color:#666; font-size:.75rem; padding: 0 .5rem .5rem; }}
</style></head><body>
<h1>{html.escape(title)}</h1>
<p>{len(entries)} photos &middot; generated {date.today().isoformat()}</p>"""]

    for month in sorted(months, reverse=True):
        parts.append(f"<h2>{html.escape(month)}</h2>")
        for e in months[month]:
            job = f' &middot; {html.escape(e["job"])}' if e["job"] else ""
            note = f'<div class="meta">{html.escape(e["note"])}</div>' if e["note"] else ""
            parts.append(f"""<div class="card">
<img src="{html.escape(e['src'])}" loading="lazy" alt="{html.escape(e['caption'])}">
<div class="cap">{html.escape(e["caption"])}{job}</div>{note}</div>""")

    parts.append("</body></html>")
    return "\n".join(parts)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--photos-dir", type=Path,
                    default=Path(os.environ.get("GARAGE_DATA_DIR", str(Path.home() / ".hermes" / "garage"))) / "photos")
    ap.add_argument("--out", default=None, help="default: <photos-dir>/index.html")
    ap.add_argument("--title", default="Restoration Progress")
    args = ap.parse_args()
    entries = collect_entries(args.photos_dir)
    out = args.out or args.photos_dir / "index.html"
    out.write_text(render(entries, args.title), encoding="utf-8")
    print(f"{len(entries)} photos -> {out}")


if __name__ == "__main__":
    main()
