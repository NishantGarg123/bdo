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
import os
from pathlib import Path
from typing import Any

import requests
from dotenv import set_key

from .config import GRAPHQL_ENDPOINT
from .id_utils import to_db_id, to_upwork_id

logger = logging.getLogger(__name__)

_TOKEN_URL = "https://www.upwork.com/api/v3/oauth2/token"
# The project root .env has priority in config.py and is the file used by the
# application deployment. If it is read-only in Docker, the process-level
# environment update below still lets the current refresh continue.
_ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"


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
    access_token = (os.getenv("UPWORK_ACCESS_TOKEN") or "").strip("'\"")
    if not access_token:
        raise EnvironmentError(
            "UPWORK_ACCESS_TOKEN is not set. "
            "Add it to backend/.env or the project root .env."
        )
    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }


def _refresh_if_needed(resp: requests.Response) -> bool:
    """Refresh a rejected access token once and make it immediately available.

    This intentionally returns only whether retrying the original request is
    appropriate. The caller owns the single retry, preventing refresh loops.
    """
    if resp.status_code != 401:
        return False

    logger.info("Got 401 — attempting token refresh…")

    refresh = (os.getenv("UPWORK_REFRESH_TOKEN") or "").strip("'\"")
    if not refresh:
        logger.error("✗ Token refresh aborted: UPWORK_REFRESH_TOKEN is not set or empty.")
        return False

    client_id = (os.getenv("UPWORK_CLIENT_KEY") or "").strip("'\"")
    client_secret = (os.getenv("UPWORK_CLIENT_SECRET") or "").strip("'\"")

    if not client_id or not client_secret:
        logger.error(
            "✗ Token refresh aborted: UPWORK_CLIENT_KEY=%s  UPWORK_CLIENT_SECRET=%s",
            "SET" if client_id else "MISSING",
            "SET" if client_secret else "MISSING",
        )
        return False

    try:
        token_response = requests.post(
            _TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh,
                "client_id": client_id,
                "client_secret": client_secret,
            },
            timeout=30,
        )
        if not token_response.ok:
            logger.error(
                "✗ Token refresh failed: Upwork returned HTTP %s. Body: %s",
                token_response.status_code,
                token_response.text[:500],
            )
            return False
        tokens = token_response.json()
        access_token = tokens.get("access_token")
        if not access_token:
            logger.error("✗ Token refresh response missing 'access_token'. Body: %s", tokens)
            return False
    except (requests.RequestException, ValueError) as exc:
        logger.error("✗ Token refresh request failed with exception: %s", exc)
        return False

    os.environ["UPWORK_ACCESS_TOKEN"] = access_token
    if tokens.get("refresh_token"):
        os.environ["UPWORK_REFRESH_TOKEN"] = tokens["refresh_token"]

    try:
        set_key(_ENV_FILE, "UPWORK_ACCESS_TOKEN", access_token)
        if tokens.get("refresh_token"):
            set_key(_ENV_FILE, "UPWORK_REFRESH_TOKEN", tokens["refresh_token"])
        logger.info("✓ New tokens written to %s", _ENV_FILE)
    except Exception:  # .env can be read-only in Docker; env values still work.
        logger.info("Could not write tokens to %s (read-only?); os.environ updated instead.", _ENV_FILE)

    logger.info("✓ Upwork access token refreshed; retrying the failed request once.")
    return True


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

    if _refresh_if_needed(response):
        try:
            response = requests.post(
                GRAPHQL_ENDPOINT,
                headers=_build_headers(),
                json={"query": query, "variables": variables or {}},
                timeout=30,
            )
        except requests.RequestException as exc:
            logger.error("âœ— Network error retrying Upwork GraphQL API: %s", exc)
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
