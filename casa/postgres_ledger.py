"""
Postgres-backed governance decision ledger.

When DATABASE_URL is set, decisions are written to a Postgres table instead of
(or in addition to) the flat ledger.log file.  All existing read paths fall back
gracefully to the file-backed ledger when no database is available, so the
system works without Postgres in development or on Render free tier.

Schema (auto-created on first write):

    CREATE TABLE IF NOT EXISTS governance_decisions (
        decision_id   UUID PRIMARY KEY,
        created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
        agent         TEXT NOT NULL,
        action        TEXT NOT NULL,
        risk          JSONB,
        decision      TEXT NOT NULL,
        signals       JSONB NOT NULL DEFAULT '{}'::jsonb,
        policy_version TEXT NOT NULL,
        review_status  TEXT DEFAULT 'unreviewed',
        review_notes   TEXT,
        reviewed_at    TIMESTAMPTZ
    );
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")

# Lazy connection pool – created only when DATABASE_URL is present.
_pool = None

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS governance_decisions (
    decision_id    TEXT PRIMARY KEY,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    agent          TEXT NOT NULL,
    action         TEXT NOT NULL,
    risk           JSONB,
    decision       TEXT NOT NULL,
    signals        JSONB NOT NULL DEFAULT '{}'::jsonb,
    policy_version TEXT NOT NULL,
    review_status  TEXT DEFAULT 'unreviewed',
    review_notes   TEXT,
    reviewed_at    TIMESTAMPTZ
);
"""

_INSERT_SQL = """
INSERT INTO governance_decisions
    (decision_id, agent, action, risk, decision, signals, policy_version)
VALUES (%s, %s, %s, %s::jsonb, %s, %s::jsonb, %s)
ON CONFLICT (decision_id) DO NOTHING;
"""

_SELECT_ALL_SQL = """
SELECT decision_id, created_at, agent, action, risk, decision,
       signals, policy_version, review_status, review_notes, reviewed_at
FROM governance_decisions
ORDER BY created_at ASC;
"""

_SELECT_BY_ID_SQL = """
SELECT decision_id, created_at, agent, action, risk, decision,
       signals, policy_version, review_status, review_notes, reviewed_at
FROM governance_decisions
WHERE decision_id = %s;
"""

_UPDATE_REVIEW_SQL = """
UPDATE governance_decisions
SET review_status = %s, review_notes = %s, reviewed_at = now()
WHERE decision_id = %s;
"""


def _get_connection():
    """Return a psycopg2 connection, or None if unavailable."""
    global _pool
    if not _DATABASE_URL:
        return None
    try:
        import psycopg2  # type: ignore
        conn = psycopg2.connect(_DATABASE_URL)
        return conn
    except Exception as exc:  # pragma: no cover
        logger.warning("Postgres unavailable, falling back to file ledger: %s", exc)
        return None


def _ensure_table(conn) -> None:
    """Create the governance_decisions table if it doesn't exist."""
    with conn.cursor() as cur:
        cur.execute(_CREATE_TABLE_SQL)
    conn.commit()


def is_available() -> bool:
    """Return True when a Postgres backend is reachable."""
    if not _DATABASE_URL:
        return False
    conn = _get_connection()
    if conn is None:
        return False
    conn.close()
    return True


def write_decision(
    decision_id: str,
    agent: str,
    action: str,
    risk: Any,
    decision: str,
    signals: Dict[str, Any],
    policy_version: str,
) -> bool:
    """
    Persist a governance decision to Postgres.

    Returns True on success, False if Postgres is unavailable.
    """
    conn = _get_connection()
    if conn is None:
        return False
    try:
        _ensure_table(conn)
        with conn.cursor() as cur:
            cur.execute(
                _INSERT_SQL,
                (
                    decision_id,
                    agent,
                    action,
                    json.dumps(risk),
                    decision,
                    json.dumps(signals),
                    policy_version,
                ),
            )
        conn.commit()
        return True
    except Exception as exc:  # pragma: no cover
        logger.error("Failed to write decision to Postgres: %s", exc)
        return False
    finally:
        conn.close()


def read_decisions() -> List[Dict[str, Any]]:
    """
    Read all decisions from Postgres.

    Returns an empty list if Postgres is unavailable.
    """
    conn = _get_connection()
    if conn is None:
        return []
    try:
        _ensure_table(conn)
        with conn.cursor() as cur:
            cur.execute(_SELECT_ALL_SQL)
            rows = cur.fetchall()
        return [_row_to_dict(row) for row in rows]
    except Exception as exc:  # pragma: no cover
        logger.error("Failed to read decisions from Postgres: %s", exc)
        return []
    finally:
        conn.close()


def get_decision_by_id(decision_id: str) -> Optional[Dict[str, Any]]:
    """Return a single decision dict or None."""
    conn = _get_connection()
    if conn is None:
        return None
    try:
        _ensure_table(conn)
        with conn.cursor() as cur:
            cur.execute(_SELECT_BY_ID_SQL, (decision_id,))
            row = cur.fetchone()
        return _row_to_dict(row) if row else None
    except Exception as exc:  # pragma: no cover
        logger.error("Failed to fetch decision %s from Postgres: %s", decision_id, exc)
        return None
    finally:
        conn.close()


def update_review_status(
    decision_id: str, review_status: str, review_notes: str = ""
) -> bool:
    """Update the review_status of a decision.  Returns True on success."""
    conn = _get_connection()
    if conn is None:
        return False
    try:
        _ensure_table(conn)
        with conn.cursor() as cur:
            cur.execute(_UPDATE_REVIEW_SQL, (review_status, review_notes, decision_id))
        conn.commit()
        return True
    except Exception as exc:  # pragma: no cover
        logger.error("Failed to update review status in Postgres: %s", exc)
        return False
    finally:
        conn.close()


def _row_to_dict(row) -> Dict[str, Any]:
    """Convert a DB row tuple to a governance decision dict."""
    (
        decision_id,
        created_at,
        agent,
        action,
        risk,
        decision,
        signals,
        policy_version,
        review_status,
        review_notes,
        reviewed_at,
    ) = row

    # psycopg2 returns JSONB columns as already-parsed Python objects
    risk_val = risk if not isinstance(risk, str) else json.loads(risk)
    signals_val = signals if not isinstance(signals, str) else json.loads(signals)

    return {
        "decision_id": decision_id,
        "time": created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at),
        "agent": agent,
        "action": action,
        "risk": risk_val,
        "decision": decision,
        "signals": signals_val or {},
        "policy_version": policy_version,
        "review_status": review_status,
        "review_notes": review_notes,
        "reviewed_at": reviewed_at.isoformat() if reviewed_at and hasattr(reviewed_at, "isoformat") else None,
    }
