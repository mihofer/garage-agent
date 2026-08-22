#!/usr/bin/env python3
"""Generate a log-scaled spectrogram PNG from an audio file via ffmpeg.

Thin wrapper so the agent has one stable command; the ffmpeg filter matches
the garage-audio skill.

Usage: spectrogram.py input.m4a output.png
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def make_spectrogram(src: str | Path, dst: str | Path) -> Path:
    src, dst = Path(src), Path(dst)
    if not src.exists():
        raise FileNotFoundError(src)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src),
           "-lavfi", "showspectrumpic=s=1024x512:legend=1:scale=log", str(dst)]
    subprocess.run(cmd, check=True)
    return dst


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    out = make_spectrogram(sys.argv[1], sys.argv[2])
    print(out)
