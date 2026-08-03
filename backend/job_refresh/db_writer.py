"""
job_refresh.db_writer
~~~~~~~~~~~~~~~~~~~~~
Persists refreshed job-activity data to the database.

The four refresh targets live in the ``public.analyses`` table (not in
``jobs``), matching the design used by the Django bulk-refresh API endpoint.
The writer uses a direct psycopg2 connection so it can run as a standalone
script completely independently of the Django ORM.

Table: public.analyses
Required columns (created automatically if absent):
  - job_id         TEXT  (primary/join key)
  - proposal_draft TEXT  (existing — not modified here)
  - interviewing   BOOLEAN
  - invite_sent    BOOLEAN
  - hired          BOOLEAN

The ``jobs.total_proposals`` column IS updated because it is part of the
core job record and is the canonical proposal count shown in the UI.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Generator

import psycopg2
from psycopg2.extensions import connection as PgConnection

from .config import DB_CONFIG
from .upwork_client import JobActivityResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Connection helpers
# ---------------------------------------------------------------------------

@contextmanager
def _get_connection() -> Generator[PgConnection, None, None]:
    """Yield a psycopg2 connection and ensure it is closed afterwards."""
    conn: PgConnection = psycopg2.connect(**DB_CONFIG)
    try:
        yield conn
    finally:
        conn.close()


def _ensure_analyses_columns(conn: PgConnection) -> None:
    """Add tracking columns to public.analyses if they do not yet exist.

    Uses ALTER TABLE … ADD COLUMN IF NOT EXISTS so this is always safe to
    call — it is a no-op when the columns already exist.
    """
    cols = [
        ("interviewing", "BOOLEAN DEFAULT FALSE"),
        ("invite_sent", "BOOLEAN DEFAULT FALSE"),
        ("hired", "BOOLEAN DEFAULT FALSE"),
    ]
    with conn.cursor() as cur:
        for col_name, col_def in cols:
            try:
                cur.execute(
                    f"ALTER TABLE public.analyses "
                    f"ADD COLUMN IF NOT EXISTS {col_name} {col_def}"
                )
                conn.commit()
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Could not ensure column public.analyses.%s: %s",
                    col_name,
                    exc,
                )
                conn.rollback()


# ---------------------------------------------------------------------------
# Write helpers
# ---------------------------------------------------------------------------

def _upsert_analyses_row(conn: PgConnection, result: JobActivityResult) -> bool:
    """Upsert the three boolean tracking fields in public.analyses.

    If no analysis row exists yet for the job, a minimal stub row is inserted
    so the refresh data is not silently lost.

    Returns True on success, False on error.
    """
    sql = """
        INSERT INTO public.analyses (job_id, interviewing, invite_sent, hired)
        VALUES (%(job_id)s, %(interviewing)s, %(invite_sent)s, %(hired)s)
        ON CONFLICT (job_id) DO UPDATE
            SET interviewing = EXCLUDED.interviewing,
                invite_sent  = EXCLUDED.invite_sent,
                hired        = EXCLUDED.hired
    """
    params = {
        "job_id": result.job_id,
        "interviewing": result.interviewing,
        "invite_sent": result.invite_sent,
        "hired": result.hired,
    }
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
        conn.commit()
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "Failed to upsert analyses row for job %r: %s",
            result.job_id,
            exc,
        )
        conn.rollback()
        return False


def _update_job_proposals(conn: PgConnection, result: JobActivityResult) -> bool:
    """Update jobs.total_proposals with the latest applicant count.

    Returns True on success (including when the job row does not exist),
    False on database error.
    """
    sql = """
        UPDATE jobs
        SET total_proposals = %(count)s
        WHERE id = %(job_id)s
    """
    try:
        with conn.cursor() as cur:
            cur.execute(sql, {"count": result.total_applicants, "job_id": result.job_id})
        conn.commit()
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "Failed to update total_proposals for job %r: %s",
            result.job_id,
            exc,
        )
        conn.rollback()
        return False


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

class WriteResult:
    """Outcome of a single write operation."""

    __slots__ = ("job_id", "analyses_ok", "proposals_ok")

    def __init__(self, job_id: str, *, analyses_ok: bool, proposals_ok: bool) -> None:
        self.job_id = job_id
        self.analyses_ok = analyses_ok
        self.proposals_ok = proposals_ok

    @property
    def success(self) -> bool:
        return self.analyses_ok and self.proposals_ok

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<WriteResult job_id={self.job_id!r} "
            f"analyses_ok={self.analyses_ok} "
            f"proposals_ok={self.proposals_ok}>"
        )


def persist_refresh_result(result: JobActivityResult) -> WriteResult:
    """Write one :class:`JobActivityResult` to the database.

    Opens a dedicated connection for this operation so the caller does not
    need to manage connection state.
    """
    with _get_connection() as conn:
        _ensure_analyses_columns(conn)
        analyses_ok = _upsert_analyses_row(conn, result)
        proposals_ok = _update_job_proposals(conn, result)

    return WriteResult(
        result.job_id,
        analyses_ok=analyses_ok,
        proposals_ok=proposals_ok,
    )


def persist_refresh_results(results: list[JobActivityResult]) -> list[WriteResult]:
    """Batch-write a list of :class:`JobActivityResult` objects.

    Uses a single shared connection for efficiency.
    """
    write_results: list[WriteResult] = []

    with _get_connection() as conn:
        _ensure_analyses_columns(conn)

        for result in results:
            analyses_ok = _upsert_analyses_row(conn, result)
            proposals_ok = _update_job_proposals(conn, result)
            write_results.append(
                WriteResult(
                    result.job_id,
                    analyses_ok=analyses_ok,
                    proposals_ok=proposals_ok,
                )
            )

    return write_results
