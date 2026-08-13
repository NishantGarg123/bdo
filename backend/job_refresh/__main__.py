#!/usr/bin/env python3
"""
job_refresh CLI entry-point
~~~~~~~~~~~~~~~~~~~~~~~~~~~
Accepts one or more Upwork job IDs and refreshes their data in the database.

Usage
-----
    # From the backend/ directory:
    python -m job_refresh <job_id> [<job_id> ...]

    # Or directly:
    python backend/job_refresh/__main__.py <job_id> [<job_id> ...]

Examples
--------
    python -m job_refresh ~01abc1234567890a ~02def9876543210b

    # Read job IDs from a file (one per line):
    python -m job_refresh $(cat my_ids.txt | tr '\\n' ' ')

Exit codes
----------
    0  All jobs refreshed successfully (or nothing to do).
    1  One or more jobs failed to fetch or write.
    2  Bad arguments / configuration error.
"""

from __future__ import annotations

import argparse
import logging
import sys

from .refresh_jobs import refresh_jobs


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m job_refresh",
        description=(
            "Refresh proposal / interviewing / invite_sent / hired data "
            "for one or more Upwork job IDs."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "job_ids",
        metavar="JOB_ID",
        nargs="+",
        help="One or more Upwork job IDs to refresh.",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable DEBUG-level logging.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    _configure_logging(args.verbose)

    logger = logging.getLogger("job_refresh.cli")

    try:
        summary = refresh_jobs(args.job_ids)
    except EnvironmentError as exc:
        # Raised by upwork_client when the access token is missing.
        logger.error("Configuration error: %s", exc)
        return 2
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error during refresh: %s", exc)
        return 1

    # Print a human-readable result table.
    print()
    print(f"{'JOB ID':<40}  {'FETCHED':<8}  {'WRITTEN':<8}  {'STATUS'}")
    print("-" * 72)
    for outcome in summary.outcomes:
        written = (
            "✓" if outcome.write_result and outcome.write_result.success
            else "✗" if outcome.fetched
            else "—"
        )
        status = "OK" if outcome.success else ("FETCH FAILED" if not outcome.fetched else "WRITE FAILED")
        print(f"{outcome.job_id:<40}  {'✓' if outcome.fetched else '✗':<8}  {written:<8}  {status}")
    print("-" * 72)
    print(f"Total: {summary.total}  Succeeded: {summary.succeeded}  "
          f"Failed: {summary.total - summary.succeeded}")
    print()

    return 0 if summary.succeeded == summary.total else 1


if __name__ == "__main__":
    sys.exit(main())
