#!/usr/bin/env python3
"""OBD-II telemetry sidecar (Phase 3).

Connects to an ELM327 adapter (USB serial recommended), samples PIDs into
telemetry.sqlite, records DTC events, and writes alert files the agent's
heartbeat can pick up.

Modes:
  default          connect to real adapter (--port /dev/ttyUSB0)
  --simulate       synthetic data at ~1 Hz — no hardware needed (dev/testing)

Requires the `obd` package only in real/simulate runs (lazy import).
Schema lives in obd_schema() and matches mcp_server/obd_server.py.
"""

from __future__ import annotations

import argparse
import math
import os
import random
import signal
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(os.environ.get("GARAGE_DATA_DIR", str(Path.home() / ".hermes" / "garage")))
DB_PATH = DATA_DIR / "telemetry.sqlite"
ALERT_DIR = DATA_DIR / "alerts"

SAMPLE_PIDS = ["RPM", "COOLANT_TEMP", "ENGINE_LOAD", "SHORT_FUEL_TRIM_1",
               "LONG_FUEL_TRIM_1", "SPEED", "INTAKE_TEMP", "THROTTLE_POS"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY, started TEXT NOT NULL, ended TEXT,
    source TEXT NOT NULL DEFAULT 'obd');
CREATE TABLE IF NOT EXISTS samples (
    session_id INTEGER NOT NULL REFERENCES sessions(id),
    ts TEXT NOT NULL, pid TEXT NOT NULL, value REAL);
CREATE INDEX IF NOT EXISTS idx_samples ON samples(session_id, pid, ts);
CREATE TABLE IF NOT EXISTS dtc_events (
    id INTEGER PRIMARY KEY, ts TEXT NOT NULL, code TEXT NOT NULL,
    description TEXT DEFAULT '', status TEXT NOT NULL DEFAULT 'active');
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def init_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    ALERT_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.executescript(SCHEMA)
    con.commit()
    return con


def write_alert(code: str, description: str) -> None:
    path = ALERT_DIR / f"dtc-{code}-{int(time.time())}.txt"
    path.write_text(
        f"NEW DTC DETECTED\n"
        f"ts: {now()}\ncode: {code}\ndescription: {description}\n"
        f"Do NOT clear codes without owner confirmation (freeze-frame evidence).\n")
    print(f"ALERT written: {path}")


# ------------------------------------------------------------------- real

def read_real(con: sqlite3.Connection, port: str) -> None:
    import obd  # lazy: only needed with hardware
    logging_stub = getattr(obd, "OBD", None)
    if logging_stub is None:
        print("python-OBD not installed"); sys.exit(2)
    connection = obd.OBD(portstr=port)
    if connection.status() != obd.OBDStatus.CAR_CONNECTED:
        print("no car connected on", port); sys.exit(3)
    commands = [obd.commands[n] for n in SAMPLE_PIDS if obd.commands.has_name(n)]
    session = con.execute(
        "INSERT INTO sessions (started, source) VALUES (?, ?)", (now(), "obd")).lastrowid
    con.commit()
    stop = {"flag": False}
    signal.signal(signal.SIGTERM, lambda *_: stop.update(flag=True))

    known_dtc = set()
    while not stop["flag"]:
        ts = now()
        rows = []
        for cmd in commands:
            resp = connection.query(cmd)
            if not resp.is_null():
                rows.append((session, ts, cmd.name, float(resp.value.magnitude)))
        con.executemany("INSERT INTO samples (session_id, ts, pid, value) VALUES (?,?,?,?)", rows)
        con.commit()
        resp = connection.query(obd.commands.GET_DTC)
        for code, desc in (resp.value or []):
            if code and code != "P0000" and code not in known_dtc:
                known_dtc.add(code)
                con.execute("INSERT INTO dtc_events (ts, code, description) VALUES (?,?,?)",
                            (ts, code, desc))
                con.commit()
                write_alert(code, desc)
        time.sleep(1.0)
    con.execute("UPDATE sessions SET ended=? WHERE id=?", (now(), session))
    con.commit()


# -------------------------------------------------------------- simulated

def read_simulated(con: sqlite3.Connection, duration_s: float) -> None:
    session = con.execute(
        "INSERT INTO sessions (started, source) VALUES (?, ?)",
        (now(), "simulate")).lastrowid
    con.commit()
    t0 = time.time()
    tick = 0
    injected = False
    while time.time() - t0 < duration_s:
        ts = now()
        t = time.time() - t0
        rpm = 850 + 120 * math.sin(t / 5) + random.uniform(-30, 30)
        coolant = min(92, 55 + t * 1.5 + random.uniform(-0.4, 0.4))
        rows = [
            (session, ts, "RPM", rpm),
            (session, ts, "COOLANT_TEMP", coolant),
            (session, ts, "SPEED", max(0, 50 * math.sin(t / 12))),
            (session, ts, "SHORT_FUEL_TRIM_1", random.uniform(-4, 4)),
        ]
        # simulate a fault appearing mid-session to exercise alerting
        if not injected and t > duration_s * 0.4:
            injected = True
            con.execute("INSERT INTO dtc_events (ts, code, description) VALUES (?,?,?)",
                        (ts, "P0128", "Coolant Thermostat (Coolant Temp Below Regulating Temp)"))
            con.commit()
            write_alert("P0128", "simulated thermostat fault")
        con.executemany("INSERT INTO samples (session_id, ts, pid, value) VALUES (?,?,?,?)", rows)
        con.commit()
        tick += 1
        time.sleep(max(0.0, tick - (time.time() - t0)))
    con.execute("UPDATE sessions SET ended=? WHERE id=?", (now(), session))
    con.commit()
    n = con.execute("SELECT COUNT(*) FROM samples WHERE session_id=?", (session,)).fetchone()[0]
    print(f"session {session}: {n} samples over {duration_s:.0f}s")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port", default="/dev/ttyUSB0")
    ap.add_argument("--simulate", action="store_true")
    ap.add_argument("--duration", type=float, default=60.0,
                    help="simulate mode duration in seconds")
    args = ap.parse_args()
    con = init_db()
    try:
        if args.simulate:
            read_simulated(con, args.duration)
        else:
            read_real(con, args.port)
    finally:
        con.close()


if __name__ == "__main__":
    main()
