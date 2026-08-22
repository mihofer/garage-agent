"""Ledger schema integrity: apply schema.sql and exercise the rules it encodes."""
import sqlite3
from pathlib import Path

import pytest

SCHEMA = Path(__file__).resolve().parent.parent / "ledger" / "schema.sql"


@pytest.fixture()
def db(tmp_path):
    con = sqlite3.connect(tmp_path / "ledger.sqlite")
    con.executescript(SCHEMA.read_text())
    con.execute("PRAGMA foreign_keys = ON")
    yield con
    con.close()


def test_status_constraints(db):
    db.execute("INSERT INTO parts(name, status) VALUES ('pump', 'needed')")
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("UPDATE parts SET status='bogus' WHERE name='pump'")
    db.execute("UPDATE parts SET status='ordered' WHERE name='pump'")  # ok

    db.execute("INSERT INTO orders(part_id, shop, total, status) VALUES (1,'s',50,'placed')")
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("UPDATE orders SET status='lost'")


def test_foreign_key_usage_log(db):
    db.execute("INSERT INTO consumables(kind, name, qty_on_hand, unit) VALUES ('fluid','oil',4,'l')")
    db.execute("INSERT INTO usage_log(consumable_id, quantity) VALUES (1, 0.5)")  # ok
    try:
        db.execute("INSERT INTO usage_log(consumable_id, quantity) VALUES (999, 1)")
        raised = False
    except sqlite3.IntegrityError:
        raised = True
    assert raised, "usage_log must reject unknown consumable ids"


def test_budget_views(db):
    rows = [("parts", "discs", 120), ("parts", "pads", 60),
            ("tools", "torque wrench", 90)]
    db.executemany(
        "INSERT INTO costs(category, description, amount) VALUES (?,?,?)", rows)
    cats = dict(db.execute("SELECT category, total FROM budget_by_category"))
    assert cats["parts"] == 180.0 and cats["tools"] == 90.0

    db.execute("INSERT INTO costs(category, description, amount, job) "
               "VALUES ('parts','brake job bits',40,'brakes')")
    jobs = dict(db.execute("SELECT job, total FROM budget_by_job"))
    assert jobs["brakes"] == 40.0


def test_open_parts_view(db):
    db.executemany("INSERT INTO parts(name, status) VALUES (?, ?)",
                   [("a", "needed"), ("b", "installed"), ("c", "found")])
    names = [r[0] for r in db.execute("SELECT name FROM open_parts")]
    assert sorted(names) == ["a", "c"]


def test_updated_at_trigger(db):
    db.execute("INSERT INTO parts(name) VALUES ('x')")
    old = db.execute("SELECT updated_at FROM parts WHERE name='x'").fetchone()[0]
    db.execute("UPDATE parts SET price=10 WHERE name='x'")
    new = db.execute("SELECT updated_at FROM parts WHERE name='x'").fetchone()[0]
    assert new >= old
