"""Inline per-page OCR fallback: image-only PDFs must yield text."""
import subprocess
import sys
from pathlib import Path

import pytest

BUILD = Path(__file__).resolve().parent.parent / "ingest" / "build_index.py"


def _make_scanned_pdf(path: Path) -> None:
    """Render text to pixels and wrap in a PDF -> an image-only PDF."""
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (1200, 400), "white")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.load_default(size=64)
    except TypeError:  # older Pillow
        font = ImageFont.load_default()
    draw.text((50, 160), "BRAKE CALIPER TORQUE 110 NM", fill="black", font=font)
    img.save(path, "PDF", resolution=100)


@pytest.mark.skipif(
    subprocess.run(["which", "tesseract"], capture_output=True).returncode != 0,
    reason="tesseract binary not installed",
)
def test_image_only_pdf_is_ocrd(tmp_path):
    pdf = tmp_path / "scan.pdf"
    _make_scanned_pdf(pdf)

    spec = import_module(BUILD)
    pages = spec.extract_pages(pdf, ocr=True)

    assert len(pages) == 1
    page_no, text = pages[0]
    assert page_no == 1
    # OCR is imperfect on rendered fonts; look for the load-bearing content
    assert "TORQUE" in text.upper()
    assert any(ch.isdigit() for ch in text)


def import_module(path):
    import importlib.util
    spec = importlib.util.spec_from_file_location("build_index", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
