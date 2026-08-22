"""garage-obd MCP server (Phase 3): query the telemetry sidecar's SQLite.

Read-only. Expects scripts/obd-daemon.py to be running (real or --simulate).
"""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

from fastmcp import FastMCP

_data_dir = Path(os.environ.get("GARAGE_DATA_DIR", str(Path.home() / ".hermes" / "garage")))
DB_PATH = Path(os.environ.get("GARAGE_TELEMETRY_DB", str(_data_dir / "telemetry.sqlite")))

mcp = FastMCP("garage-obd")


def _con() -> sqlite3.Connection:
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


@mcp.tool()
def obd_status() -> str:
    """Telemetry availability: open sessions, sample counts, latest activity."""
    if not DB_PATH.exists():
        return json.dumps({"status": "no telemetry database — OBD daemon not running"})
    con = _con()
    try:
        sessions = [dict(r) for r in con.execute(
            "SELECT id, started, ended, source FROM sessions ORDER BY id DESC LIMIT 5")]
        total = con.execute("SELECT COUNT(*) FROM samples").fetchone()[0]
        last = con.execute("SELECT MAX(ts) AS last FROM samples").fetchone()["last"]
        alerts = sorted((Path(os.environ.get(
            "GARAGE_ALERT_DIR", str(DB_PATH.parent / "alerts")))).glob("dtc-*.txt"))
        return json.dumps({
            "recent_sessions": sessions, "total_samples": total, "last_sample": last,
            "unhandled_alerts": [a.name for a in alerts]}, ensure_ascii=False)
    finally:
        con.close()


@mcp.tool()
def obd_snapshot() -> str:
    """Most recent value per PID from the latest session."""
    if not DB_PATH.exists():
        return json.dumps({"error": "no telemetry database"})
    con = _con()
    try:
        rows = [dict(r) for r in con.execute("""
            SELECT pid, value, ts FROM samples
            WHERE session_id = (SELECT MAX(id) FROM sessions)
              AND ts = (SELECT MAX(ts) FROM samples
                        WHERE session_id=(SELECT MAX(id) FROM sessions))
              AND rowid IN (SELECT MAX(rowid) FROM samples
                            WHERE session_id=(SELECT MAX(id) FROM sessions) GROUP BY pid)
        """)]
        return json.dumps(rows, ensure_ascii=False)
    finally:
        con.close()


@mcp.tool()
def obd_dtc() -> str:
    """Stored DTC fault-code events. Never clear codes without owner confirmation."""
    if not DB_PATH.exists():
        return json.dumps({"error": "no telemetry database"})
    con = _con()
    try:
        rows = [dict(r) for r in con.execute(
            "SELECT ts, code, description, status FROM dtc_events ORDER BY id DESC LIMIT 50")]
        return json.dumps(rows, ensure_ascii=False)
    finally:
        con.close()


@mcp.tool()
def obd_history(pid: str, minutes: int = 15) -> str:
    """Time series of one PID over the last N minutes of the current session."""
    if not DB_PATH.exists():
        return json.dumps({"error": "no telemetry database"})
    con = _con()
    try:
        rows = [dict(r) for r in con.execute(
            """SELECT ts, value FROM samples
               WHERE pid=? AND session_id=(SELECT MAX(id) FROM sessions)
                 AND ts >= datetime('now', ?)
               ORDER BY ts""", (pid.upper(), f"-{int(minutes)} minutes"))]
        vals = [r["value"] for r in rows]
        summary = {"pid": pid, "n": len(vals),
                   "min": min(vals) if vals else None,
                   "max": max(vals) if vals else None}
        return json.dumps({"summary": summary, "series": rows[-200:]}, ensure_ascii=False)
    finally:
        con.close()


if __name__ == "__main__":
    mcp.run()
