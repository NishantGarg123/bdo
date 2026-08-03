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

import logging
from typing import Any

import requests

from .config import GRAPHQL_ENDPOINT, UPWORK_ACCESS_TOKEN

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# GraphQL queries
# ---------------------------------------------------------------------------

# Fetches the activity stats for a single job by its Upwork ID.
# Fields chosen to cover all four refresh targets:
#   proposal      → totalApplicants  (number of proposals submitted)
#   interviewing  → totalInvitedToInterview > 0
#   invite_sent   → invitesSent > 0
#   hired         → totalHired > 0
_QUERY_JOB_ACTIVITY = """
query getJobActivity($jobId: ID!) {
  marketplaceJobPosting(id: $jobId) {
    id
    totalApplicants
    activityStat {
      jobActivity {
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

    Returns ``None`` on HTTP errors or when the response contains GraphQL
    errors, after logging a descriptive message.  Callers must handle ``None``.
    """
    try:
        response = requests.post(
            GRAPHQL_ENDPOINT,
            headers=_build_headers(),
            json={"query": query, "variables": variables or {}},
            timeout=30,
        )
    except requests.RequestException as exc:
        logger.error("Network error calling Upwork GraphQL API: %s", exc)
        return None

    if response.status_code != 200:
        logger.error(
            "Upwork API returned HTTP %s: %s",
            response.status_code,
            response.text[:400],
        )
        return None

    payload: dict[str, Any] = response.json()

    if "errors" in payload:
        logger.error(
            "Upwork GraphQL errors for query variables %s: %s",
            variables,
            payload["errors"],
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
        total_applicants: int,
        invites_sent: int,
        total_invited_to_interview: int,
        total_hired: int,
        raw: dict[str, Any],
    ) -> None:
        self.job_id = job_id
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
            f"proposals={self.total_applicants} "
            f"interviewing={self.interviewing} "
            f"invite_sent={self.invite_sent} "
            f"hired={self.hired}>"
        )


def fetch_job_activity(job_id: str) -> JobActivityResult | None:
    """Fetch the latest activity stats for a single Upwork job.

    Parameters
    ----------
    job_id:
        The Upwork job ID (the same string stored in the ``jobs`` table).

    Returns
    -------
    A :class:`JobActivityResult` on success, or ``None`` if the API call
    failed or the job was not found.
    """
    payload = _execute(_QUERY_JOB_ACTIVITY, {"jobId": job_id})
    if payload is None:
        return None

    posting: dict[str, Any] | None = (
        payload.get("data", {}).get("marketplaceJobPosting")
    )

    if not posting:
        logger.warning("Job ID %r not found in Upwork API response.", job_id)
        return None

    activity: dict[str, Any] = (
        posting.get("activityStat", {}).get("jobActivity", {}) or {}
    )

    return JobActivityResult(
        job_id=job_id,
        total_applicants=int(posting.get("totalApplicants") or 0),
        invites_sent=int(activity.get("invitesSent") or 0),
        total_invited_to_interview=int(activity.get("totalInvitedToInterview") or 0),
        total_hired=int(activity.get("totalHired") or 0),
        raw=posting,
    )
