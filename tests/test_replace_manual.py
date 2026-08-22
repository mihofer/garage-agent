"""replace_manual: re-indexing the same manual must not duplicate chunks."""
import pytest

from mcp_server import knowledge


def test_replace_manual_drops_only_that_manual(con):
    for manual, text in [("FSM-A", "brake torque 110 Nm"), ("FSM-A", "axle specs page"),
                         ("FSM-B", "engine oil 4.5 l")]:
        knowledge.add_manual_chunk(con, manual, 1, text)
    # add_manual_chunk commits; FTS rows follow chunks 1:1

    removed = knowledge.replace_manual(con, "FSM-A")
    assert removed == 2
    remaining = [r["manual"] for r in con.execute("SELECT manual FROM chunks")]
    assert remaining == ["FSM-B"]
    # FTS stays in sync: searching removed content finds nothing
    assert knowledge.fts_search(con, "brake torque", None) == {}
    assert len(knowledge.fts_search(con, "engine oil", None)) == 1


def test_replace_nonexistent_is_noop(con):
    assert knowledge.replace_manual(con, "ghost") == 0
