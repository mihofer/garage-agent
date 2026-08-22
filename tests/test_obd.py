"""OBD daemon: DB schema + simulate-mode run + alert generation (no hardware)."""
import sqlite3
import subprocess
import sys
from pathlib import Path

DAEMON = Path(__file__).resolve().parent.parent / "scripts" / "obd-daemon.py"


def test_simulate_run_creates_db_alerts_and_closes_session(tmp_path, monkeypatch):
    monkeypatch.setenv("GARAGE_DATA_DIR", str(tmp_path))
    r = subprocess.run(
        [sys.executable, str(DAEMON), "--simulate", "--duration", "3"],
        capture_output=True, text=True, timeout=60,
        env={**__import__("os").environ, "GARAGE_DATA_DIR": str(tmp_path)})
    assert r.returncode == 0, r.stderr

    db = tmp_path / "telemetry.sqlite"
    assert db.exists()
    con = sqlite3.connect(db)
    sessions = con.execute("SELECT started, ended, source FROM sessions").fetchall()
    assert len(sessions) == 1 and sessions[0][1] is not None      # closed
    assert con.execute("SELECT COUNT(*) FROM samples").fetchone()[0] > 3
    dtc = con.execute("SELECT code, description FROM dtc_events").fetchall()
    assert any(code == "P0128" for code, _ in dtc)
    con.close()

    alerts = list((tmp_path / "alerts").glob("dtc-*.txt"))
    assert len(alerts) == 1
    assert "P0128" in alerts[0].read_text()


def test_obd_server_queries_read_the_db(tmp_path):
    """obd_server SQL works against a daemon-produced DB (import without fastmcp)."""
    import importlib.util

    # produce data first
    env = {**__import__("os").environ, "GARAGE_DATA_DIR": str(tmp_path)}
    subprocess.run([sys.executable, str(DAEMON), "--simulate", "--duration", "2"],
                   check=True, capture_output=True, timeout=60, env=env)

    spec = importlib.util.spec_from_file_location(
        "obd_server", Path(__file__).resolve().parent.parent / "mcp_server" / "obd_server.py")
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)   # needs fastmcp; skip cleanly if absent
    except ImportError:
        import pytest
        pytest.skip("fastmcp not installed")

    monkey = tmp_path
    mod.DB_PATH = monkey / "telemetry.sqlite"

    status = __import__("json").loads(mod.obd_status())
    assert status["total_samples"] > 0
    snap = __import__("json").loads(mod.obd_snapshot())
    pids = {r["pid"] for r in snap}
    assert {"RPM", "COOLANT_TEMP"} <= pids
    hist = __import__("json").loads(mod.obd_history("RPM", minutes=60))
    assert hist["summary"]["n"] > 0 and hist["summary"]["min"] > 0
