#!/usr/bin/env python3
"""Generate the KITT scanner-light GIF (red sweep with fading tail).

Pure ffmpeg under the hood: renders one PNG per frame with stacked drawbox
filters (bright head + dimming trail), then assembles a palettized,
infinitely looping GIF.

Usage: make_kitt_gif.py [output.gif]
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

W, H = 256, 56
HEAD_W, HEAD_H = 14, 14
Y = (H - HEAD_H) // 2
FRAMES = 36
FPS = 18
TRAIL = [(0xFF2020, 10), (0xB01010, 9), (0x780808, 8), (0x400404, 7)]


def positions() -> list[int]:
    """Triangle wave: head sweeps left->right->left across the bar."""
    span = W - HEAD_W
    out = []
    for f in range(FRAMES):
        phase = (f * 6) % (2 * span)
        out.append(phase if phase <= span else 2 * span - phase)
    return out


def frame_filter(pos: int) -> str:
    boxes = [f"drawbox=x={pos}:y={Y}:w={HEAD_W}:h={HEAD_H}:color=0xFF1414:t=fill"]
    direction = 1 if pos < W // 2 else -1  # tail streams opposite to travel
    offset = HEAD_W
    for color, width in TRAIL:
        tx = pos - direction * offset - (width if direction == 1 else 0)
        tx = max(0, min(W - width, tx))
        boxes.append(f"drawbox=x={tx}:y={Y + 2}:w={width}:h={HEAD_H - 4}:color=0x{color:06X}:t=fill")
        offset += width
    return ",".join(boxes)


def make_gif(out: Path) -> Path:
    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg not found")
    tmp = Path(tempfile.mkdtemp(prefix="kittgif"))
    try:
        for i, pos in enumerate(positions()):
            subprocess.run(
                ["ffmpeg", "-y", "-loglevel", "error",
                 "-f", "lavfi", "-i", f"color=c=0x000000:s={W}x{H}:d=1",
                 "-frames:v", "1", "-vf", frame_filter(pos),
                 str(tmp / f"f{i:03d}.png")],
                check=True)
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error",
             "-framerate", str(FPS), "-i", str(tmp / "f%03d.png"),
             "-filter_complex",
             "[0:v]split[a][b];[a]palettegen=max_colors=32[p];[b][p]paletteuse",
             "-loop", "0", str(out)],
            check=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return out


if __name__ == "__main__":
    dst = Path(sys.argv[1] if len(sys.argv) > 1 else "kitt_scanner.gif")
    print(make_gif(dst))
