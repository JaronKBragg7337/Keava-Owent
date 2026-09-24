"""
store/db.py — the single durable substrate.

Everything that must survive a restart lives here: the internal state, the
append-only ledger, the memory graph snapshot pointer, the approval queue, and
the action-receipt chain. We use Python's standard-library sqlite3 deliberately:
no server, no extra dependency, runs the same on a laptop or a cloud VM. This is
the "continuity" guarantee from ECIH made concrete — the system can be killed at
any moment and come back knowing what it knew.
"""

import sqlite3
import os
import json
import threading
from datetime import datetime, timezone

# One lock per process. SQLite handles its own file locking, but the loop is
# single-threaded by design (a never-ending loop, not a thread pool), so this is
# mostly belt-and-suspenders for the scheduler thread.
_LOCK = threading.Lock()


def utc_now_iso() -> str:
    """Single source of truth for timestamps. Always UTC, always ISO-8601.

    Time matters here because the Live-Reference engine judges staleness by
    comparing 'now' against when a reading was taken. If timestamps drifted
    between naive local time and UTC, a fresh reading could look stale or a
    stale one could look fresh — which would quietly break the whole
    live-reference guarantee. So every timestamp in the system comes through
    this one function.
    """
    return datetime.now(timezone.utc).isoformat()


class Store:
    """Thin wrapper over a SQLite file. Holds the five tables the system needs."""

    def __init__(self, path: str):
        self.path = path
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self._init_schema()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with _LOCK, self._conn() as conn:
            conn.executescript(
                """
                -- The single mutable state row (id is always 1). This is the
                -- thing ECIH says the system must regulate and keep coherent.
                CREATE TABLE IF NOT EXISTS state (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    payload TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                -- The standing-condition ledger. APPEND ONLY. We never UPDATE
                -- or DELETE a ledger row, because the ledger is a history of
                -- what the system cost and what it did, and rewriting history
                -- is exactly the "claim a zero you never measured" failure.
                CREATE TABLE IF NOT EXISTS ledger (
                    event_id TEXT PRIMARY KEY,
                    cycle_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    consumption TEXT NOT NULL,
                    contribution TEXT NOT NULL,
                    note TEXT
                );

                -- Actions waiting on a human yes/no (LOCK-mode and anything the
                -- membrane flags high-impact). The human-in-the-loop gate.
                CREATE TABLE IF NOT EXISTS approvals (
                    approval_id TEXT PRIMARY KEY,
                    cycle_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    action TEXT NOT NULL,
                    status TEXT NOT NULL,          -- PENDING / APPROVED / DENIED
                    decided_at TEXT
                );

                -- Hash-chained receipts: what the system did and that it was
                -- authorized. NOT proof it was valuable — see ledger contribution.
                CREATE TABLE IF NOT EXISTS receipts (
                    receipt_id TEXT PRIMARY KEY,
                    cycle_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    action TEXT NOT NULL,
                    result TEXT,
                    prev_hash TEXT NOT NULL,
                    this_hash TEXT NOT NULL,
                    signature TEXT
                );

                -- Human verdicts on what the system did. This is the honest
                -- substitute for the (open) contribution unit: we do not SCORE
                -- contribution, we RECORD an external human judgment of it.
                CREATE TABLE IF NOT EXISTS verdicts (
                    verdict_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    source TEXT NOT NULL,          -- e.g. an allowlisted email
                    refers_to TEXT,                -- receipt_id or cycle_id it judges
                    verdict TEXT NOT NULL,         -- helped / neutral / did_not_help / harmful
                    raw TEXT                       -- the original message text
                );
                """
            )

    # ---- state ---------------------------------------------------------------

    def load_state(self):
        with _LOCK, self._conn() as conn:
            row = conn.execute("SELECT payload FROM state WHERE id = 1").fetchone()
            return json.loads(row["payload"]) if row else None

    def save_state(self, payload: dict) -> None:
        with _LOCK, self._conn() as conn:
            conn.execute(
                "INSERT INTO state (id, payload, updated_at) VALUES (1, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET payload = excluded.payload, "
                "updated_at = excluded.updated_at",
                (json.dumps(payload), utc_now_iso()),
            )

    # ---- ledger (append only) -----------------------------------------------

    def append_ledger(self, event: dict) -> None:
        with _LOCK, self._conn() as conn:
            conn.execute(
                "INSERT INTO ledger (event_id, cycle_id, created_at, consumption, "
                "contribution, note) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    event["event_id"],
                    event["cycle_id"],
                    event["created_at"],
                    json.dumps(event["consumption"]),
                    json.dumps(event["contribution"]),
                    event.get("note", ""),
                ),
            )

    def ledger_totals(self) -> dict:
        """Sum the cost side (which is known) and count the contribution side
        (which is, by design, NOT summed into a value — only counted by status).
        Returns the honest deficit picture: cost known, contribution unscored.
        """
        with _LOCK, self._conn() as conn:
            rows = conn.execute(
                "SELECT consumption, contribution FROM ledger"
            ).fetchall()
        total_kwh = 0.0
        total_water = 0.0
        measured = 0
        unmeasured = 0
        for r in rows:
            c = json.loads(r["consumption"])
            total_kwh += float(c.get("total_energy_kwh", 0.0) or 0.0)
            total_water += float(c.get("water_liters_estimate", 0.0) or 0.0)
            contrib = json.loads(r["contribution"])
            if contrib.get("status") == "MEASURED":
                measured += 1
            else:
                unmeasured += 1
        return {
            "total_energy_kwh": total_kwh,
            "total_water_liters_estimate": total_water,
            "contribution_events_measured": measured,
            "contribution_events_unmeasured": unmeasured,
            "events": len(rows),
        }

    # ---- approvals -----------------------------------------------------------

    def enqueue_approval(self, approval_id, cycle_id, action) -> None:
        with _LOCK, self._conn() as conn:
            conn.execute(
                "INSERT INTO approvals (approval_id, cycle_id, created_at, action, "
                "status) VALUES (?, ?, ?, ?, 'PENDING')",
                (approval_id, cycle_id, utc_now_iso(), json.dumps(action)),
            )

    def pending_approvals(self) -> list:
        with _LOCK, self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM approvals WHERE status = 'PENDING' ORDER BY created_at"
            ).fetchall()
        return [dict(r) for r in rows]

    def decide_approval(self, approval_id, approved: bool) -> None:
        with _LOCK, self._conn() as conn:
            conn.execute(
                "UPDATE approvals SET status = ?, decided_at = ? WHERE approval_id = ?",
                ("APPROVED" if approved else "DENIED", utc_now_iso(), approval_id),
            )

    # ---- receipts (hash chain) ----------------------------------------------

    def last_receipt_hash(self) -> str:
        with _LOCK, self._conn() as conn:
            row = conn.execute(
                "SELECT this_hash FROM receipts ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
        return row["this_hash"] if row else "GENESIS"

    def append_receipt(self, receipt: dict) -> None:
        with _LOCK, self._conn() as conn:
            conn.execute(
                "INSERT INTO receipts (receipt_id, cycle_id, created_at, action, "
                "result, prev_hash, this_hash, signature) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    receipt["receipt_id"],
                    receipt["cycle_id"],
                    receipt["created_at"],
                    json.dumps(receipt["action"]),
                    json.dumps(receipt.get("result")),
                    receipt["prev_hash"],
                    receipt["this_hash"],
                    receipt.get("signature"),
                ),
            )

    # ---- verdicts (the honest contribution record) ---------------------------

    def append_verdict(self, verdict: dict) -> None:
        with _LOCK, self._conn() as conn:
            conn.execute(
                "INSERT INTO verdicts (verdict_id, created_at, source, refers_to, "
                "verdict, raw) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    verdict["verdict_id"],
                    verdict.get("created_at", utc_now_iso()),
                    verdict["source"],
                    verdict.get("refers_to"),
                    verdict["verdict"],
                    verdict.get("raw", ""),
                ),
            )

    def recent_verdicts(self, limit: int = 50) -> list:
        with _LOCK, self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM verdicts ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]
