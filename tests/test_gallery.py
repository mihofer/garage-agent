"""Gallery builder: sidecar parsing, ordering, HTML output."""
import json
from pathlib import Path

from scripts.build_gallery import collect_entries, render


def make_photo(photos_dir, rel_img, meta):
    img = photos_dir / rel_img
    img.parent.mkdir(parents=True, exist_ok=True)
    img.write_bytes(b"fake")
    sidecar = Path(str(img) + ".json")
    sidecar.write_text(json.dumps(meta), encoding="utf-8")


def test_collect_and_order(tmp_path):
    make_photo(tmp_path, "2025/2025-11-01_brakes/IMG_2.jpg",
               {"caption": "new discs", "job": "brakes"})
    make_photo(tmp_path, "2025/2025-11-08_engine/IMG_1.jpg",
               {"caption": "head off", "job": "engine", "note": "gasket blown"})
    make_photo(tmp_path, "2025/2025-10-05_misc/IMG_9.png", {"caption": "delivered"})

    entries = collect_entries(tmp_path)
    assert len(entries) == 3
    # newest month/day first
    assert entries[0]["day"] == "2025-11-08"
    assert entries[-1]["day"] == "2025-10-05"
    by_src = {e["src"]: e for e in entries}
    assert by_src["2025/2025-11-08_engine/IMG_1.jpg"]["note"] == "gasket blown"
    assert by_src["2025/2025-10-05_misc/IMG_9.png"]["job"] == ""


def test_render_html_escapes_and_groups(tmp_path):
    make_photo(tmp_path, "2025/2025-11-01_brakes/<b>evil</b>.jpg",
               {"caption": "<script>alert(1)</script>", "job": "brakes"})
    html = render(collect_entries(tmp_path), "T & T")
    assert "<script>" not in html          # escaped
    assert "&lt;script&gt;" in html
    assert "2025-11" in html and "T &amp; T" in html


def test_orphan_sidecars_ignored(tmp_path):
    (tmp_path / "2025").mkdir()
    (tmp_path / "2025" / "orphan.json").write_text('{"caption":"no image"}')
    assert collect_entries(tmp_path) == []


def test_broken_json_tolerated(tmp_path):
    make_photo(tmp_path, "2025/2025-01-01_x/a.jpg", {"caption": "ok"})
    (tmp_path / "2025" / "2025-01-01_x" / "a.jpg.json").write_text("{broken")
    entries = collect_entries(tmp_path)
    assert entries[0]["caption"] == "(no caption yet)"
