"""Archive import from JSONL + spectrogram script."""
import json
import subprocess
import sys
import wave
from pathlib import Path

from mcp_server import knowledge

IMPORT = Path(__file__).resolve().parent.parent / "ingest" / "import_archive.py"


def test_import_jsonl_and_search(isolated_data_dir, tmp_path):
    threads = [
        {"url": "https://f.example/t/1", "title": "Heater blows cold",
         "author": "a", "date": "2023-11-05",
         "body": "Fixed my heater: clogged matrix, backflushed it. Part 4477 kit."},
        {"url": "https://f.example/t/2", "title": "Radio code",
         "body": "Where do I find the radio code?"},
    ]
    f = tmp_path / "threads.jsonl"
    f.write_text("\n".join(json.dumps(t) for t in threads), encoding="utf-8")

    r = subprocess.run([sys.executable, str(IMPORT), str(f)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert "imported 2" in r.stdout

    hits = knowledge.search_archive("heater matrix")
    assert len(hits) == 1 and "4477" in knowledge.get_thread(hits[0]["url"])["body"]

    # re-import same file: replace, not duplicate
    subprocess.run([sys.executable, str(IMPORT), str(f)], capture_output=True, check=True)
    con = knowledge.connect()
    n = con.execute("SELECT COUNT(*) FROM archive").fetchone()[0]
    con.close()
    assert n == 2


def test_import_skips_malformed_lines(isolated_data_dir, tmp_path):
    f = tmp_path / "mixed.jsonl"
    f.write_text('{"url":"u","title":"t","body":"b"}\nnot json\n{"url":"u2"}\n',
                 encoding="utf-8")
    r = subprocess.run([sys.executable, str(IMPORT), str(f)],
                       capture_output=True, text=True)
    assert r.returncode == 0
    assert "imported 1" in r.stdout and "2 skipped" in r.stdout


# ------------------------------------------------------------- spectrogram

def _make_wav(path: Path, seconds=0.5, freq=440):
    import math
    import struct
    with wave.open(str(path), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(8000)
        frames = b"".join(
            struct.pack("<h", int(12000 * math.sin(2 * math.pi * freq * i / 8000)))
            for i in range(int(8000 * seconds)))
        w.writeframes(frames)


def test_spectrogram_produces_png(tmp_path):
    spec = Path(__file__).resolve().parent.parent / "scripts" / "spectrogram.py"
    wav = tmp_path / "tick.wav"
    png = tmp_path / "spec.png"
    _make_wav(wav)
    r = subprocess.run([sys.executable, str(spec), str(wav), str(png)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert png.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
