"""
job_refresh.refresh_jobs
~~~~~~~~~~~~~~~~~~~~~~~~
Core orchestration layer.

Accepts a list of Upwork job IDs, fetches the latest activity data for each
one in sequence, writes the results to the database, and returns a structured
summary.

This module contains no I/O concerns (no argparse, no print statements) — it
is designed to be called from the CLI entry-point, a Django management
command, the bulk-refresh API view, or a scheduler.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Sequence

from .db_writer import WriteResult, persist_refresh_results
from .upwork_client import JobActivityResult, fetch_job_activity

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class JobRefreshOutcome:
    """Full outcome for a single job ID."""

    job_id: str
    fetched: bool = False          # True if Upwork API returned data
    activity: JobActivityResult | None = None
    write_result: WriteResult | None = None

    @property
    def success(self) -> bool:
        return (
            self.fetched
            and self.write_result is not None
            and self.write_result.success
        )


@dataclass
class RefreshSummary:
    """Aggregate summary of a bulk refresh run."""

    outcomes: list[JobRefreshOutcome] = field(default_factory=list)

    # ── Convenience aggregates ──────────────────────────────────────────────

    @property
    def total(self) -> int:
        return len(self.outcomes)

    @property
    def succeeded(self) -> int:
        return sum(1 for o in self.outcomes if o.success)

    @property
    def fetch_failed(self) -> list[str]:
        return [o.job_id for o in self.outcomes if not o.fetched]

    @property
    def write_failed(self) -> list[str]:
        return [
            o.job_id
            for o in self.outcomes
            if o.fetched and (o.write_result is None or not o.write_result.success)
        ]

    def log_summary(self) -> None:
        """Emit a concise INFO-level summary to the module logger."""
        logger.info(
            "Refresh complete — total=%d succeeded=%d fetch_failed=%d write_failed=%d",
            self.total,
            self.succeeded,
            len(self.fetch_failed),
            len(self.write_failed),
        )
        if self.fetch_failed:
            logger.warning("API fetch failed for job IDs: %s", self.fetch_failed)
        if self.write_failed:
            logger.error("DB write failed for job IDs: %s", self.write_failed)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def refresh_jobs(job_ids: Sequence[str]) -> RefreshSummary:
    """Refresh activity data for every job ID in *job_ids*.

    Steps for each ID:
    1. Fetch the latest activity from the Upwork GraphQL API.
    2. If successful, batch-write all results to the database.
    3. Return a :class:`RefreshSummary` with per-job outcomes.

    Parameters
    ----------
    job_ids:
        An iterable of Upwork job ID strings.  Duplicates are silently
        deduplicated while preserving order.

    Returns
    -------
    :class:`RefreshSummary`
    """
    # Deduplicate while preserving order.
    seen: set[str] = set()
    unique_ids: list[str] = []
    for jid in job_ids:
        jid = str(jid).strip()
        if jid and jid not in seen:
            seen.add(jid)
            unique_ids.append(jid)

    if not unique_ids:
        logger.warning("refresh_jobs called with an empty job-ID list.")
        return RefreshSummary()

    logger.info("Starting refresh for %d job ID(s): %s", len(unique_ids), unique_ids)

    # ── Phase 1: fetch from Upwork API ──────────────────────────────────────
    outcomes: list[JobRefreshOutcome] = []
    successful_results: list[JobActivityResult] = []

    for job_id in unique_ids:
        logger.info("━━━ [%d/%d] Processing job_id=%r", unique_ids.index(job_id) + 1, len(unique_ids), job_id)
        outcome = JobRefreshOutcome(job_id=job_id)

        activity = fetch_job_activity(job_id)
        if activity is None:
            logger.warning("✗ Could not fetch activity for job_id=%r — skipping DB write.", job_id)
            outcomes.append(outcome)
            continue

        outcome.fetched = True
        outcome.activity = activity
        successful_results.append(activity)

        logger.info(
            "✓ Fetched job_id=%r  title=%r\n"
            "    proposals    = %d\n"
            "    interviewing = %s  (totalInvitedToInterview=%d)\n"
            "    invite_sent  = %s  (invitesSent=%d)\n"
            "    hired        = %s  (totalHired=%d)",
            job_id, activity.title,
            activity.total_applicants,
            activity.interviewing, activity.total_invited_to_interview,
            activity.invite_sent, activity.invites_sent,
            activity.hired, activity.total_hired,
        )

        outcomes.append(outcome)

    # ── Phase 2: write to the database (one connection for the whole batch) ──
    if successful_results:
        logger.info("━━━ Writing %d result(s) to the database…", len(successful_results))
        write_results = persist_refresh_results(successful_results)
        wr_map = {wr.job_id: wr for wr in write_results}

        for outcome in outcomes:
            if outcome.fetched:
                outcome.write_result = wr_map.get(outcome.job_id)

    # ── Final per-job outcome table ──────────────────────────────────────────
    logger.info("")
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info("REFRESH RESULTS:")
    logger.info("%-40s  %-8s  %-8s  %s", "JOB ID", "FETCHED", "WRITTEN", "STATUS")
    logger.info("─" * 72)
    for outcome in outcomes:
        fetched_sym = "✓" if outcome.fetched else "✗"
        written_sym = (
            "✓" if outcome.write_result and outcome.write_result.success
            else "✗" if outcome.fetched
            else "—"
        )
        status = (
            "OK" if outcome.success
            else "FETCH FAILED" if not outcome.fetched
            else "WRITE FAILED"
        )
        logger.info("%-40s  %-8s  %-8s  %s", outcome.job_id, fetched_sym, written_sym, status)
    logger.info("─" * 72)

    summary = RefreshSummary(outcomes=outcomes)
    summary.log_summary()
    return summary
