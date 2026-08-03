"""
Django management command: refresh_jobs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Fetches the latest Upwork activity stats (proposal count, interviewing,
invite_sent, hired) for one or more job IDs and persists the data to the
database.

This is a thin Django wrapper around the standalone ``job_refresh`` module.
It adds no new logic — it simply provides a ``manage.py``-compatible
entry-point so the refresh can be triggered inside the Docker container.

Usage
-----
    # Inside the container:
    docker exec -it bdo_backend python manage.py refresh_jobs <job_id> [<job_id> ...]

    # Or locally (with venv activated):
    python manage.py refresh_jobs ~01abc1234567890a ~02def9876543210b

    # Verbose output:
    python manage.py refresh_jobs --verbosity 2 <job_id>
"""

from __future__ import annotations

import logging
import sys

from django.core.management.base import BaseCommand, CommandError

# job_refresh is a sibling package of the Django apps inside backend/.
# It is not a Django app and is not in INSTALLED_APPS.
try:
    from job_refresh.refresh_jobs import RefreshSummary, refresh_jobs
except ImportError as exc:
    raise ImportError(
        "Cannot import job_refresh. "
        "Ensure the backend/ directory is on your PYTHONPATH."
    ) from exc

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Refresh Upwork activity stats (proposal / interviewing / "
        "invite_sent / hired) for one or more job IDs."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "job_ids",
            metavar="JOB_ID",
            nargs="+",
            help="One or more Upwork job IDs to refresh.",
        )

    def handle(self, *args, **options) -> None:
        job_ids: list[str] = options["job_ids"]
        verbosity: int = options.get("verbosity", 1)

        if verbosity >= 2:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.INFO)

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"Refreshing {len(job_ids)} job(s)…"
            )
        )

        try:
            summary: RefreshSummary = refresh_jobs(job_ids)
        except EnvironmentError as exc:
            raise CommandError(f"Configuration error: {exc}") from exc

        # Print result table.
        self.stdout.write("")
        header = f"{'JOB ID':<40}  {'FETCHED':<8}  {'WRITTEN':<8}  STATUS"
        self.stdout.write(header)
        self.stdout.write("-" * 72)

        for outcome in summary.outcomes:
            fetched_sym = "✓" if outcome.fetched else "✗"
            written_sym = (
                "✓" if outcome.write_result and outcome.write_result.success
                else "✗" if outcome.fetched
                else "—"
            )
            status = (
                "OK"
                if outcome.success
                else ("FETCH FAILED" if not outcome.fetched else "WRITE FAILED")
            )
            style = self.style.SUCCESS if outcome.success else self.style.ERROR
            self.stdout.write(
                style(
                    f"{outcome.job_id:<40}  {fetched_sym:<8}  {written_sym:<8}  {status}"
                )
            )

        self.stdout.write("-" * 72)
        total_line = (
            f"Total: {summary.total}  "
            f"Succeeded: {summary.succeeded}  "
            f"Failed: {summary.total - summary.succeeded}"
        )
        if summary.succeeded == summary.total:
            self.stdout.write(self.style.SUCCESS(total_line))
        else:
            self.stdout.write(self.style.ERROR(total_line))
            sys.exit(1)
