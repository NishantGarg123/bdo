"""
job_refresh.id_utils
~~~~~~~~~~~~~~~~~~~~
Utilities for converting between the two Upwork job ID representations:

  DB-stored format   → plain numeric string, no prefix, no leading zeros
                        e.g.  "2084178164356493946"

  Upwork API format  → ciphertext starting with "~0", followed by a type
                        byte ("2" for job postings), then the numeric ID
                        e.g.  "~022084178164356493946"

Upwork URL example
------------------
  https://www.upwork.com/jobs/~022084178164356493946
                                ^^^                   ← ~0  (fixed prefix)
                                   ^                  ← 2   (job-type byte)
                                    ^^^^^^^^^^^^^^^^^^← numeric ID (DB form)

Conversion rules
----------------
  DB → API   :  "~02" + db_id           →  "~022084178164356493946"
  API → DB   :  strip "~02" prefix      →  "2084178164356493946"
  Already API:  passthrough (starts with "~0")
  Already DB :  passthrough (pure digits / no prefix)

The type byte ("2") is constant for Upwork job postings.  If Upwork ever
introduces a different type byte, update JOB_TYPE_BYTE below.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# The fixed ciphertext prefix for Upwork job postings.
# "~0"  → Upwork ciphertext marker
# "2"   → entity type byte for job postings
_UPWORK_JOB_PREFIX = "~02"

# Pattern that recognises an already-formatted Upwork ciphertext.
_RE_UPWORK_ID = re.compile(r"^~0\d")

# Pattern that recognises a plain numeric DB ID.
_RE_DB_ID = re.compile(r"^\d+$")


def to_upwork_id(db_id: str) -> str:
    """Convert a DB-stored job ID to the Upwork API ciphertext format.

    Parameters
    ----------
    db_id:
        The job ID as stored in the ``jobs`` table (plain digits, no prefix).
        Already-formatted ciphertext values (starting with ``~0``) are
        returned unchanged.

    Returns
    -------
    str
        A string of the form ``~02{db_id}`` ready to pass to the Upwork
        GraphQL API as the ``id`` argument.

    Examples
    --------
    >>> to_upwork_id("2084178164356493946")
    '~022084178164356493946'

    >>> to_upwork_id("~022084178164356493946")   # already formatted
    '~022084178164356493946'
    """
    db_id = db_id.strip()

    if _RE_UPWORK_ID.match(db_id):
        # Already in Upwork ciphertext format — pass through.
        logger.debug("ID %r is already in Upwork format — no conversion needed.", db_id)
        return db_id

    if not _RE_DB_ID.match(db_id):
        logger.warning(
            "ID %r does not look like a plain numeric DB ID or a Upwork ciphertext. "
            "Attempting to use it as-is by prepending the job prefix.",
            db_id,
        )

    upwork_id = _UPWORK_JOB_PREFIX + db_id
    logger.info(
        "ID conversion  DB → Upwork:  %r  →  %r  (prepended prefix %r)",
        db_id, upwork_id, _UPWORK_JOB_PREFIX,
    )
    return upwork_id


def to_db_id(upwork_id: str) -> str:
    """Convert an Upwork API ciphertext ID to the DB-stored numeric form.

    Parameters
    ----------
    upwork_id:
        An Upwork ciphertext string such as ``~022084178164356493946``.
        Plain numeric strings (no ``~0`` prefix) are returned unchanged.

    Returns
    -------
    str
        The numeric portion of the ID (the part after ``~02``), with no
        leading zeros — exactly as it would be stored in the ``jobs`` table.

    Examples
    --------
    >>> to_db_id("~022084178164356493946")
    '2084178164356493946'

    >>> to_db_id("2084178164356493946")   # already DB format
    '2084178164356493946'
    """
    upwork_id = upwork_id.strip()

    if not _RE_UPWORK_ID.match(upwork_id):
        # Already in DB format (or unknown) — return unchanged.
        logger.debug("ID %r has no Upwork prefix — treating as DB format.", upwork_id)
        return upwork_id

    # Strip the full ~0X prefix (tilde + zero + one type byte = 3 chars).
    # Then strip any remaining leading zeros so the result matches exactly
    # what is stored in the database.
    raw = upwork_id[3:]             # drop "~02"
    db_id = raw.lstrip("0") or "0" # strip leading zeros; guard against "0"

    logger.info(
        "ID conversion  Upwork → DB:  %r  →  %r  (stripped prefix %r)",
        upwork_id, db_id, upwork_id[:3],
    )
    return db_id
