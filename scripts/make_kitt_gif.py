#!/usr/bin/env python3
"""Generate the KITT scanner-light animation (red sweep with fading tail).

Pure ffmpeg under the hood: renders one PNG per frame with stacked drawbox
filters, then assembles:
  - kitt_scanner.mp4  (H.264, silent — Telegram plays short muted mp4s as
                       looping animations; more reliable in chats than gif)
  - kitt_scanner.gif  (palettized loop — avatars, web pages, reports)

Usage: make_kitt_gif.py [output_dir]
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


def make_gif(frames_dir: Path, out: Path) -> Path:
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error",
         "-framerate", str(FPS), "-i", str(frames_dir / "f%03d.png"),
         "-filter_complex",
         "[0:v]split[a][b];[a]palettegen=max_colors=32[p];[b][p]paletteuse",
         "-loop", "0", str(out)],
        check=True)
    return out


def make_mp4(frames_dir: Path, out: Path) -> Path:
    # Silent H.264/yuv420p: Telegram plays short muted mp4s as looping
    # animations. Dimensions must be even for yuv420p.
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error",
         "-framerate", str(FPS), "-i", str(frames_dir / "f%03d.png"),
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "23",
         "-movflags", "+faststart", "-an", str(out)],
        check=True)
    return out


if __name__ == "__main__":
    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg not found")
    dst = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    dst.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="kittgif"))
    try:
        for i, pos in enumerate(positions()):
            subprocess.run(
                ["ffmpeg", "-y", "-loglevel", "error",
                 "-f", "lavfi", "-i", f"color=c=0x000000:s={W}x{H}:d=1",
                 "-frames:v", "1", "-vf", frame_filter(pos),
                 str(tmp / f"f{i:03d}.png")],
                check=True)
        print(make_mp4(tmp, dst / "kitt_scanner.mp4"))
        print(make_gif(tmp, dst / "kitt_scanner.gif"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
