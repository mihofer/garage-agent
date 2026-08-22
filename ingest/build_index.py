#!/usr/bin/env python3
"""Build the garage-knowledge index from workshop-manual PDFs.

Pipeline: extract text per page (pypdf) -> section-aware chunking ->
store in knowledge/index.sqlite (+ FTS5) -> embed chunks into vectors.npz.

Heavy deps (pypdf, sentence-transformers, numpy) are needed only here and
in the vector-search path — everything else runs on stdlib.

Usage:
  python -m ingest.build_index ./manuals/*.pdf [--no-embed]

If a PDF is a scan without a text layer, OCR first:
  ocrmypdf --skip-text manuals/scan.pdf manuals/scan-ocr.pdf
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp_server import knowledge  # noqa: E402


def extract_pages(pdf_path: Path) -> list[tuple[int, str]]:
    from pypdf import PdfReader
    reader = PdfReader(pdf_path)
    return [(i + 1, (page.extract_text() or "").strip())
            for i, page in enumerate(reader.pages)]


def build(pdf_paths: list[str], embed: bool = True) -> None:
    con = knowledge.connect()
    ids: list[str] = []
    try:
        for pdf in pdf_paths:
            manual = Path(pdf).stem
            replaced = knowledge.replace_manual(con, manual)  # idempotent re-index
            if replaced:
                print(f"  {manual}: replacing {replaced} old chunks")
            n = 0
            for page_no, page_text in extract_pages(Path(pdf)):
                if not page_text:
                    continue
                for chunk in knowledge.chunk_page(page_text):
                    rid = knowledge.add_manual_chunk(con, manual, page_no, chunk)
                    ids.append(str(rid))
                    n += 1
            print(f"  {manual}: {n} chunks")
        con.commit()

        if not ids:
            print("nothing indexed — check that PDFs have a text layer")
            return

        if embed:
            _embed(con, ids)
        else:
            con.execute(
                "INSERT OR REPLACE INTO meta (key, value) VALUES ('vector_ids', ?)",
                (json.dumps([]),))
        con.commit()
    finally:
        con.close()
    print(f"done -> {knowledge.db_path()}")


def _embed(con, chunk_ids: list[str]) -> None:
    """Embed all chunks; rebuilds vectors.npz wholesale (simple + correct)."""
    import numpy as np
    from sentence_transformers import SentenceTransformer

    model_name = "paraphrase-multilingual-mpnet-base-v2"
    rows = con.execute("SELECT id, text FROM chunks ORDER BY id").fetchall()
    print(f"embedding {len(rows)} chunks with {model_name} ...")
    model = SentenceTransformer(model_name)
    vecs = model.encode([r["text"] for r in rows], batch_size=64,
                        show_progress_bar=True, normalize_embeddings=True)
    np.savez_compressed(knowledge.index_dir() / "vectors.npz", vectors=np.asarray(vecs))
    con.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('model', ?)", (model_name,))
    con.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('vector_ids', ?)",
                (json.dumps([r["id"] for r in rows]),))
    con.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('count', ?)",
                (str(len(rows)),))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pdfs", nargs="+")
    ap.add_argument("--no-embed", action="store_true",
                    help="keyword-only index (FTS5 still works fully)")
    args = ap.parse_args()
    build(args.pdfs, embed=not args.no_embed)
