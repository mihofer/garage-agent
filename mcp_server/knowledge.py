"""garage-knowledge: pure retrieval logic over manuals + forum archive.

Stdlib only at import time. Heavy deps (numpy, sentence-transformers) are
loaded lazily inside vector_search() and degrade gracefully when missing,
so this module is testable everywhere.

Storage (under GARAGE_DATA_DIR, default ~/.hermes/garage):
  knowledge/index.sqlite   chunks+FTS5 (manuals), archive+FTS5 (forum threads)
  knowledge/vectors.npz    chunk embeddings
  knowledge/meta.json      {"model": ..., "count": N, "vector_ids": [rowids]}
"""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

CHUNK_SIZE = 1200

SCHEMA = """
CREATE TABLE IF NOT EXISTS chunks (
    id INTEGER PRIMARY KEY, manual TEXT NOT NULL, page INTEGER NOT NULL, text TEXT NOT NULL);
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    text, content='chunks', content_rowid='id');
CREATE TABLE IF NOT EXISTS archive (
    id INTEGER PRIMARY KEY, url TEXT UNIQUE NOT NULL, title TEXT NOT NULL,
    author TEXT DEFAULT '', date TEXT DEFAULT '', body TEXT NOT NULL);
CREATE VIRTUAL TABLE IF NOT EXISTS archive_fts USING fts5(
    title, body, content='archive', content_rowid='id');
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_chunks_manual ON chunks(manual, page);
"""


def data_dir() -> Path:
    return Path(os.environ.get("GARAGE_DATA_DIR", str(Path.home() / ".hermes" / "garage")))


def index_dir() -> Path:
    return data_dir() / "knowledge"


def db_path() -> Path:
    return index_dir() / "index.sqlite"


def connect(create: bool = True) -> sqlite3.Connection:
    if create:
        index_dir().mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path())
    con.row_factory = sqlite3.Row
    if create:
        con.executescript(SCHEMA)
        con.commit()
    return con


# ---------------------------------------------------------------- chunking

def chunk_page(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = 150) -> list[str]:
    """Split on paragraph boundaries; hard-split oversized blocks.

    Hard-split blocks advance with `overlap` chars of context carry-over so
    specs near a split point remain retrievable from both sides.
    """
    paragraphs = [p for p in _split_paragraphs(text) if p]
    chunks: list[str] = []
    buf = ""
    for para in paragraphs:
        while len(para) > chunk_size:
            if buf:
                chunks.append(buf)
                buf = ""
            cut = para.rfind(" ", chunk_size // 2)
            if cut == -1:
                cut = chunk_size
            chunks.append(para[:cut].strip())
            para = para[max(cut - overlap, 0):]
        if not para:
            continue
        if len(buf) + len(para) + 1 > chunk_size:
            chunks.append(buf.strip())
            buf = para
        else:
            buf = f"{buf}\n{para}" if buf else para
    if buf.strip():
        chunks.append(buf.strip())
    return [c for c in chunks if c]


def _split_paragraphs(text: str) -> list[str]:
    import re
    return [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]


# ------------------------------------------------------------- manuals FTS

def add_manual_chunk(con: sqlite3.Connection, manual: str, page: int, text: str) -> int:
    cur = con.execute(
        "INSERT INTO chunks (manual, page, text) VALUES (?, ?, ?)", (manual, page, text))
    con.execute("INSERT INTO chunks_fts (rowid, text) VALUES (?, ?)", (cur.lastrowid, text))
    con.commit()
    return cur.lastrowid


def replace_manual(con: sqlite3.Connection, manual: str) -> int:
    """Drop all chunks of `manual` (re-index is idempotent). Returns removed count.

    Call BEFORE re-ingesting a manual. Vector metadata is rebuilt wholesale by
    ingest.build_index._embed(), so it stays consistent.
    """
    con.execute(
        "DELETE FROM chunks_fts WHERE rowid IN (SELECT id FROM chunks WHERE manual=?)",
        (manual,))
    cur = con.execute("DELETE FROM chunks WHERE manual=?", (manual,))
    con.commit()
    return cur.rowcount


def fts_search(con: sqlite3.Connection, query: str, manual: str | None, limit: int = 20) -> dict[int, float]:
    """BM25 keyword search over manual chunks. Lower bm25 = better."""
    sql = ("SELECT rowid, bm25(chunks_fts) AS score FROM chunks_fts WHERE chunks_fts MATCH ?"
           + (" AND rowid IN (SELECT id FROM chunks WHERE manual = ?)" if manual else "")
           + " ORDER BY score LIMIT ?")
    args = [_fts_escape(query)] + ([manual] if manual else []) + [limit]
    try:
        rows = con.execute(sql, args).fetchall()
    except sqlite3.OperationalError:
        return {}
    return {r["rowid"]: 1.0 / (1e-6 - r["score"]) for r in rows}


def _fts_escape(query: str) -> str:
    """Quote each term so part numbers like 'M12x1.5' don't break FTS syntax."""
    terms = [t for t in query.replace('"', " ").split() if t]
    return " ".join(f'"{t}"' for t in terms)


# ---------------------------------------------------------- manuals vector

def vector_ids(con: sqlite3.Connection) -> list[int] | None:
    row = con.execute("SELECT value FROM meta WHERE key='vector_ids'").fetchone()
    return json.loads(row["value"]) if row else None


def vector_search(con: sqlite3.Connection, query: str, manual: str | None,
                  limit: int = 20) -> dict[int, float]:
    """Cosine similarity over precomputed embeddings. Lazy heavy imports."""
    try:
        import numpy as np
        from sentence_transformers import SentenceTransformer
    except ImportError:
        return {}
    meta_file = index_dir() / "meta.json"
    vec_file = index_dir() / "vectors.npz"
    if not meta_file.exists() or not vec_file.exists():
        return {}
    meta = json.loads(meta_file.read_text())
    ids = vector_ids(con) or []
    if not ids or len(ids) != meta.get("count", -1):
        return {}
    model = SentenceTransformer(meta["model"])
    qvec = model.encode([query], normalize_embeddings=True)[0]
    vecs = np.load(vec_file)["vectors"]
    sims = vecs @ qvec
    hits: dict[int, float] = {}
    for idx in np.argsort(-sims):
        rid = ids[int(idx)]
        if manual and not con.execute(
                "SELECT 1 FROM chunks WHERE id=? AND manual=?", (rid, manual)).fetchone():
            continue
        hits[rid] = float(sims[idx])
        if len(hits) >= limit:
            break
    return hits


def reciprocal_rank_fusion(*rankings: dict[int, float], k: int = 60) -> list[int]:
    scores: dict[int, float] = {}
    for ranking in rankings:
        for rank, (rid, _) in enumerate(sorted(ranking.items(), key=lambda kv: -kv[1])):
            scores[rid] = scores.get(rid, 0.0) + 1.0 / (k + rank + 1)
    return [rid for rid, _ in sorted(scores.items(), key=lambda kv: -kv[1])]


def search_manuals(query: str, manual: str | None = None, limit: int = 5) -> list[dict]:
    con = connect()
    try:
        fts = fts_search(con, query, manual, limit=25)
        vec = vector_search(con, query, manual, limit=25)
        ranked = reciprocal_rank_fusion(fts, vec)[:limit]
        out = []
        for rid in ranked:
            row = con.execute(
                "SELECT manual, page, text FROM chunks WHERE id=?", (rid,)).fetchone()
            if row:
                out.append({"manual": row["manual"], "page": row["page"],
                            "text": row["text"][:1500]})
        return out
    finally:
        con.close()


def get_page(manual: str, page: int) -> dict:
    con = connect()
    try:
        rows = con.execute(
            "SELECT text FROM chunks WHERE manual=? AND page=? ORDER BY id",
            (manual, page)).fetchall()
        if not rows:
            return {"error": f"no text found for {manual} p.{page}"}
        return {"manual": manual, "page": page, "text": "\n\n".join(r["text"] for r in rows)}
    finally:
        con.close()


def list_manuals() -> list[dict]:
    con = connect()
    try:
        rows = con.execute(
            "SELECT manual, COUNT(*) AS n FROM chunks GROUP BY manual ORDER BY manual").fetchall()
        return [{"manual": r["manual"], "chunks": r["n"]} for r in rows]
    finally:
        con.close()


# ----------------------------------------------------------------- archive

def add_archive_entry(con: sqlite3.Connection, url: str, title: str,
                      author: str, date: str, body: str) -> int:
    old = con.execute("SELECT id FROM archive WHERE url=?", (url,)).fetchone()
    if old:  # replace
        con.execute("DELETE FROM archive_fts WHERE rowid=?", (old["id"],))
        con.execute("DELETE FROM archive WHERE id=?", (old["id"],))
    cur = con.execute(
        "INSERT INTO archive (url, title, author, date, body) VALUES (?, ?, ?, ?, ?)",
        (url, title, author, date, body))
    con.execute("INSERT INTO archive_fts (rowid, title, body) VALUES (?, ?, ?)",
                (cur.lastrowid, title, body))
    con.commit()
    return cur.lastrowid


def search_archive(query: str, limit: int = 8) -> list[dict]:
    con = connect()
    try:
        try:
            rows = con.execute(
                "SELECT a.url, a.title, a.author, a.date,"
                " snippet(archive_fts, 1, '>>>', '<<<', '…', 24) AS snip"
                " FROM archive_fts JOIN archive a ON a.id = archive_fts.rowid"
                " WHERE archive_fts MATCH ?"
                " ORDER BY bm25(archive_fts) LIMIT ?", (_fts_escape(query), limit)).fetchall()
        except sqlite3.OperationalError:
            return []
        return [{"url": r["url"], "title": r["title"], "author": r["author"],
                 "date": r["date"], "snippet": r["snip"]} for r in rows]
    finally:
        con.close()


def get_thread(url: str) -> dict:
    con = connect()
    try:
        row = con.execute(
            "SELECT url, title, author, date, body FROM archive WHERE url=?", (url,)).fetchone()
        return dict(row) if row else {"error": f"thread not found: {url}"}
    finally:
        con.close()
