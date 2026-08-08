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
  - job_id         TEXT  (join key — may or may not have a UNIQUE constraint)
  - proposal_draft TEXT  (existing — not modified here)
  - interviewing   BOOLEAN
  - invite_sent    BOOLEAN
  - hired          BOOLEAN

The ``jobs.total_proposals`` column IS updated because it is part of the
core job record and is the canonical proposal count shown in the UI.

Notes on the upsert strategy
-----------------------------
We use UPDATE-first then INSERT-if-needed rather than ON CONFLICT because:
  - The analyses table is externally managed and may not have a UNIQUE
    constraint on job_id that ON CONFLICT requires.
  - This approach is always safe regardless of the table's constraint set.
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
    logger.debug(
        "Opening DB connection  host=%s  port=%s  dbname=%s  user=%s",
        DB_CONFIG.get("host"), DB_CONFIG.get("port"),
        DB_CONFIG.get("dbname"), DB_CONFIG.get("user"),
    )
    conn: PgConnection = psycopg2.connect(**DB_CONFIG)
    try:
        yield conn
    finally:
        conn.close()
        logger.debug("DB connection closed.")


def _ensure_analyses_columns(conn: PgConnection) -> None:
    """Add tracking columns to public.analyses if they do not yet exist.

    Each ALTER TABLE is executed in its own transaction so a failure on one
    column does not abort the others.
    """
    cols = [
        ("interviewing", "BOOLEAN DEFAULT FALSE"),
        ("invite_sent",  "BOOLEAN DEFAULT FALSE"),
        ("hired",        "BOOLEAN DEFAULT FALSE"),
    ]
    for col_name, col_def in cols:
        # Each DDL needs its own connection state (auto-commit) to avoid
        # leaving the connection in an error state for the next statement.
        try:
            with conn.cursor() as cur:
                sql = (
                    f"ALTER TABLE public.analyses "
                    f"ADD COLUMN IF NOT EXISTS {col_name} {col_def}"
                )
                logger.debug("DDL: %s", sql)
                cur.execute(sql)
            conn.commit()
            logger.debug("✓ Column public.analyses.%s ensured.", col_name)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Could not ensure column public.analyses.%s — %s "
                "(continuing — column may already exist with a different type)",
                col_name, exc,
            )
            conn.rollback()


# ---------------------------------------------------------------------------
# Write helpers
# ---------------------------------------------------------------------------

def _upsert_analyses_row(conn: PgConnection, result: JobActivityResult) -> bool:
    """Write the three boolean tracking fields to public.analyses.

    Strategy: UPDATE first; if no row was matched, INSERT a stub row.
    This avoids the ON CONFLICT requirement for a UNIQUE constraint on job_id.

    Returns True on success, False on error.
    """
    # ── Step 1: attempt UPDATE ──────────────────────────────────────────────
    update_sql = """
        UPDATE public.analyses
        SET interviewing = %(interviewing)s,
            invite_sent  = %(invite_sent)s,
            hired        = %(hired)s
        WHERE job_id = %(job_id)s
    """
    params = {
        "job_id":      result.job_id,
        "interviewing": result.interviewing,
        "invite_sent":  result.invite_sent,
        "hired":        result.hired,
    }

    try:
        with conn.cursor() as cur:
            logger.info(
                "DB UPDATE public.analyses  job_id=%r  interviewing=%s  invite_sent=%s  hired=%s",
                result.job_id, result.interviewing, result.invite_sent, result.hired,
            )
            cur.execute(update_sql, params)
            rows_updated = cur.rowcount

        conn.commit()
        logger.info(
            "✓ UPDATE public.analyses  job_id=%r  rows_affected=%d",
            result.job_id, rows_updated,
        )

    except Exception as exc:  # noqa: BLE001
        logger.error(
            "✗ UPDATE public.analyses failed for job_id=%r: %s",
            result.job_id, exc,
        )
        conn.rollback()
        return False

    if rows_updated > 0:
        return True

    # ── Step 2: no existing row → INSERT a stub ──────────────────────────────
    logger.info(
        "No existing analyses row for job_id=%r — inserting stub row.", result.job_id
    )
    insert_sql = """
        INSERT INTO public.analyses (job_id, interviewing, invite_sent, hired)
        VALUES (%(job_id)s, %(interviewing)s, %(invite_sent)s, %(hired)s)
    """
    try:
        with conn.cursor() as cur:
            logger.info("DB INSERT public.analyses  job_id=%r", result.job_id)
            cur.execute(insert_sql, params)
        conn.commit()
        logger.info("✓ INSERT public.analyses  job_id=%r  OK", result.job_id)
        return True

    except Exception as exc:  # noqa: BLE001
        logger.error(
            "✗ INSERT public.analyses failed for job_id=%r: %s",
            result.job_id, exc,
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
    params = {"count": result.total_applicants, "job_id": result.job_id}
    try:
        with conn.cursor() as cur:
            logger.info(
                "DB UPDATE jobs.total_proposals  job_id=%r  new_value=%d",
                result.job_id, result.total_applicants,
            )
            cur.execute(sql, params)
            rows_updated = cur.rowcount
        conn.commit()
        logger.info(
            "✓ UPDATE jobs.total_proposals  job_id=%r  rows_affected=%d",
            result.job_id, rows_updated,
        )
        if rows_updated == 0:
            logger.warning(
                "⚠ No row in jobs table matched job_id=%r — "
                "total_proposals not updated (job may not exist in DB).",
                result.job_id,
            )
        return True

    except Exception as exc:  # noqa: BLE001
        logger.error(
            "✗ UPDATE jobs.total_proposals failed for job_id=%r: %s",
            result.job_id, exc,
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
    """Write one :class:`JobActivityResult` to the database."""
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

    Uses a single shared connection for the whole batch.
    """
    write_results: list[WriteResult] = []

    with _get_connection() as conn:
        _ensure_analyses_columns(conn)

        for result in results:
            logger.info("─── Writing DB record for job_id=%r ───", result.job_id)
            analyses_ok = _upsert_analyses_row(conn, result)
            proposals_ok = _update_job_proposals(conn, result)
            wr = WriteResult(
                result.job_id,
                analyses_ok=analyses_ok,
                proposals_ok=proposals_ok,
            )
            logger.info(
                "DB write complete  job_id=%r  analyses_ok=%s  proposals_ok=%s  overall=%s",
                result.job_id, analyses_ok, proposals_ok, wr.success,
            )
            write_results.append(wr)

    return write_results
