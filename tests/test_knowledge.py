"""Tests for garage-knowledge retrieval (keyword path; vectors degrade to no-op)."""
import json

import pytest

from mcp_server import knowledge


def _seed_manual(con, n_pages=3):
    for page in range(1, n_pages + 1):
        text = f"Front brake caliper bracket torque is {page * 10} Nm. Page {page} of the brake chapter."
        rid = knowledge.add_manual_chunk(con, "FSM-Test", page, text)
        con.execute("INSERT INTO chunks_fts (rowid, text) VALUES (?, ?)", (rid, text))
    con.commit()


def test_schema_created(con):
    tables = {r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table','view')")}
    assert {"chunks", "chunks_fts", "archive", "archive_fts", "meta"} <= tables


def test_fts_search_finds_part_number(con):
    _seed_manual(con)
    hits = knowledge.fts_search(con, '"bracket" "torque"', None)
    assert len(hits) == 3


def test_fts_escape_allows_special_chars(con):
    con.execute("INSERT INTO chunks (manual, page, text) VALUES ('M', 1, 'Bolt M12x1.5 torque spec')")
    con.execute("INSERT INTO chunks_fts (rowid, text) SELECT id, text FROM chunks")
    con.commit()
    # raw query with dot would break FTS syntax; escaped must work
    hits = knowledge.fts_search(con, "M12x1.5", None)
    assert len(hits) == 1


def test_search_manuals_with_citation_fields(con):
    _seed_manual(con)
    results = knowledge.search_manuals("caliper bracket torque", limit=2)
    assert 0 < len(results) <= 2
    for r in results:
        assert r["manual"] == "FSM-Test"
        assert isinstance(r["page"], int) and r["text"]


def test_vector_search_missing_model_is_noop(con):
    _seed_manual(con)
    # no meta.json/vectors.npz -> graceful empty
    assert knowledge.vector_search(con, "anything", None) == {}
    # and hybrid search still returns keyword results
    assert len(knowledge.search_manuals("torque")) > 0


def test_get_page_and_list_manuals(con):
    _seed_manual(con)
    page = knowledge.get_page("FSM-Test", 2)
    assert "20 Nm" in page["text"]
    assert knowledge.get_page("FSM-Test", 99).get("error")
    manuals = knowledge.list_manuals()
    assert manuals == [{"manual": "FSM-Test", "chunks": 3}]


# ------------------------------------------------------------------ archive

def test_archive_roundtrip(con):
    knowledge.add_archive_entry(
        con, "https://forum.example/t/1", "Noisy lifters fix",
        "wrencher", "2024-02-01",
        "Cold start tick fixed by replacing the lifter kit part 12345.")
    knowledge.add_archive_entry(
        con, "https://forum.example/t/2", "Unrelated thread",
        "a", "2024-03-01", "Best wax for paint?")
    res = knowledge.search_archive("lifter tick")
    assert len(res) == 1
    assert "lifter" in res[0]["snippet"].lower()
    thread = knowledge.get_thread("https://forum.example/t/1")
    assert "12345" in thread["body"]


def test_archive_replace_on_same_url(con):
    knowledge.add_archive_entry(con, "u1", "t1", "", "", "old body words")
    knowledge.add_archive_entry(con, "u1", "t1", "", "", "new body words")
    rows = con.execute("SELECT COUNT(*) FROM archive").fetchone()[0]
    fts_rows = con.execute(
        "SELECT COUNT(*) FROM archive_fts WHERE archive_fts MATCH 'body'").fetchone()[0]
    assert rows == 1
    assert fts_rows == 1
    assert "new body" in knowledge.get_thread("u1")["body"]


def test_rrf_prefers_consensus():
    a = {1: 3.0, 2: 2.0}
    b = {2: 0.9, 1: 0.8}
    ranked = knowledge.reciprocal_rank_fusion(a, b)
    assert ranked[0] in (1, 2)          # both appear in both rankings
    assert set(ranked) == {1, 2}


def test_rrf_empty_rankings():
    assert knowledge.reciprocal_rank_fusion({}, {}) == []
