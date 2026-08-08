"""
job_refresh.upwork_client
~~~~~~~~~~~~~~~~~~~~~~~~~
Thin wrapper around the Upwork GraphQL API.

Only exposes the single operation needed by the refresh module:
fetching activity stats for a known job ID.

No job-search / pagination logic from the legacy script is included here —
this module is intentionally scoped to single-job lookups.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import requests

from .config import GRAPHQL_ENDPOINT, UPWORK_ACCESS_TOKEN
from .id_utils import to_db_id, to_upwork_id

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# GraphQL queries
# ---------------------------------------------------------------------------

# Fetches the activity stats for a single job by its Upwork ID.
# Fields mirror what the reference script (Jobs_list.py) uses:
#   proposal      → totalApplicants   (total proposals submitted)
#   interviewing  → totalInvitedToInterview > 0
#   invite_sent   → invitesSent > 0
#   hired         → totalHired > 0
_QUERY_JOB_ACTIVITY = """
query getJobActivity($jobId: ID!) {
  marketplaceJobPosting(id: $jobId) {
    id
    content {
      title
    }
    activityStat {
      jobActivity {
        lastClientActivity
        invitesSent
        totalInvitedToInterview
        totalHired
        totalUnansweredInvites
        totalOffered
      }
    }
  }
}
"""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_headers() -> dict[str, str]:
    """Return the HTTP headers required for every Upwork GraphQL request."""
    if not UPWORK_ACCESS_TOKEN:
        raise EnvironmentError(
            "UPWORK_ACCESS_TOKEN is not set. "
            "Add it to backend/.env or the project root .env."
        )
    return {
        "Authorization": f"Bearer {UPWORK_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }


def _execute(query: str, variables: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Send a GraphQL request and return the parsed JSON response.

    Logs the full raw response at INFO level so callers can see exactly
    what the Upwork API returned.

    Returns ``None`` on HTTP errors or when the response contains GraphQL
    errors, after logging a descriptive message.  Callers must handle ``None``.
    """
    vars_str = json.dumps(variables or {})
    logger.info("→ Upwork API request  endpoint=%s  variables=%s", GRAPHQL_ENDPOINT, vars_str)

    try:
        response = requests.post(
            GRAPHQL_ENDPOINT,
            headers=_build_headers(),
            json={"query": query, "variables": variables or {}},
            timeout=30,
        )
    except requests.RequestException as exc:
        logger.error("✗ Network error calling Upwork GraphQL API: %s", exc)
        return None

    logger.info("← Upwork API response  HTTP %s", response.status_code)

    if response.status_code != 200:
        logger.error(
            "✗ Upwork API returned HTTP %s. Body: %s",
            response.status_code,
            response.text[:800],
        )
        return None

    # Log the raw JSON so the user can see exactly what came back.
    try:
        payload: dict[str, Any] = response.json()
    except ValueError:
        logger.error("✗ Upwork API returned non-JSON body: %s", response.text[:400])
        return None

    logger.info(
        "← Upwork API raw payload:\n%s",
        json.dumps(payload, indent=2, default=str),
    )

    if "errors" in payload:
        logger.error(
            "✗ Upwork GraphQL errors for job %s:\n%s",
            vars_str,
            json.dumps(payload["errors"], indent=2),
        )
        return None

    return payload


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

class JobActivityResult:
    """Structured result from a single job-activity lookup."""

    __slots__ = (
        "job_id",
        "title",
        "total_applicants",
        "invites_sent",
        "total_invited_to_interview",
        "total_hired",
        "raw",
    )

    def __init__(
        self,
        *,
        job_id: str,
        title: str,
        total_applicants: int,
        invites_sent: int,
        total_invited_to_interview: int,
        total_hired: int,
        raw: dict[str, Any],
    ) -> None:
        self.job_id = job_id
        self.title = title
        self.total_applicants = total_applicants
        self.invites_sent = invites_sent
        self.total_invited_to_interview = total_invited_to_interview
        self.total_hired = total_hired
        self.raw = raw

    # Convenience boolean properties used by the DB writer.
    @property
    def invite_sent(self) -> bool:
        return self.invites_sent > 0

    @property
    def interviewing(self) -> bool:
        return self.total_invited_to_interview > 0

    @property
    def hired(self) -> bool:
        return self.total_hired > 0

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<JobActivityResult job_id={self.job_id!r} "
            f"title={self.title!r} "
            f"proposals={self.total_applicants} "
            f"interviewing={self.interviewing} ({self.total_invited_to_interview}) "
            f"invite_sent={self.invite_sent} ({self.invites_sent}) "
            f"hired={self.hired} ({self.total_hired})>"
        )


def fetch_job_activity(job_id: str) -> JobActivityResult | None:
    """Fetch the latest activity stats for a single Upwork job.

    Parameters
    ----------
    job_id:
        The ID stored in ``jobs`` (normally a numeric ID without the leading
        zero/type prefix).  Ciphertext IDs are also accepted for CLI use.

    Returns
    -------
    A :class:`JobActivityResult` on success, or ``None`` if the API call
    failed or the job was not found.
    """
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    stored_job_id = to_db_id(job_id)
    upwork_job_id = to_upwork_id(job_id)
    logger.info(
        "Fetching Upwork activity: stored_job_id=%r upwork_job_id=%r",
        stored_job_id,
        upwork_job_id,
    )

    payload = _execute(_QUERY_JOB_ACTIVITY, {"jobId": upwork_job_id})
    if payload is None:
        logger.error("✗ API call returned no payload for stored_job_id=%r", stored_job_id)
        return None

    posting: dict[str, Any] | None = (
        payload.get("data", {}).get("marketplaceJobPosting")
    )

    if not posting:
        logger.error(
            "✗ 'marketplaceJobPosting' key missing or null for job_id=%r. "
            "Full data section: %s",
            upwork_job_id,
            json.dumps(payload.get("data"), indent=2, default=str),
        )
        return None

    activity: dict[str, Any] = (
        (posting.get("activityStat") or {}).get("jobActivity") or {}
    )

    title: str = (posting.get("content") or {}).get("title") or "(unknown)"
    total_applicants = int(posting.get("totalApplicants") or 0)
    invites_sent = int(activity.get("invitesSent") or 0)
    total_invited = int(activity.get("totalInvitedToInterview") or 0)
    total_hired = int(activity.get("totalHired") or 0)

    logger.info(
        "✓ Parsed activity for job_id=%r  title=%r\n"
        "    totalApplicants          = %d  → proposal\n"
        "    invitesSent              = %d  → invite_sent = %s\n"
        "    totalInvitedToInterview  = %d  → interviewing = %s\n"
        "    totalHired               = %d  → hired = %s",
        stored_job_id, title,
        total_applicants,
        invites_sent, invites_sent > 0,
        total_invited, total_invited > 0,
        total_hired, total_hired > 0,
    )

    return JobActivityResult(
        # Writers must use the exact database representation, not the
        # ciphertext value accepted by the Upwork API.
        job_id=stored_job_id,
        title=title,
        total_applicants=total_applicants,
        invites_sent=invites_sent,
        total_invited_to_interview=total_invited,
        total_hired=total_hired,
        raw=posting,
    )
