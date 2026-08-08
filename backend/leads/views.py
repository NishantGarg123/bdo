"""
Job API views — list, create, retrieve, update, delete.
"""

from datetime import timedelta
import logging

from django.db import connection, transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from activity.models import Activity, ActivityType

from .models import Job, LeadStatus
from .serializers import LeadSerializer


logger = logging.getLogger(__name__)


def _ensure_rejected_leads_table():
    """Create the rejected_leads table (and any missing columns) if needed.

    Runs in autocommit mode so DDL commits immediately, independent of the
    outer request transaction.
    """
    with connection.cursor() as cursor:
        old_autocommit = connection.autocommit
        connection.set_autocommit(True)
        try:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS rejected_leads (
                    id TEXT PRIMARY KEY,
                    rejection_reason TEXT NOT NULL
                )
                """
            )
            # Add the title column if it was not present in an earlier version.
            cursor.execute(
                """
                ALTER TABLE rejected_leads
                ADD COLUMN IF NOT EXISTS title TEXT
                """
            )
        finally:
            connection.set_autocommit(old_autocommit)

PAGE_SIZE = 50

TIME_FILTERS = {
    "24h": timedelta(hours=24),
    "3d": timedelta(days=3),
    "7d": timedelta(days=7),
    "14d": timedelta(days=14),
    "30d": timedelta(days=30),
    "all": None,
}


def filter_jobs(queryset, *, search="", status_filter="", time_filter="24h"):
    """Apply the lead-list filters consistently to results and status totals."""
    if search:
        queryset = queryset.filter(
            Q(title__icontains=search)
            | Q(job_type__icontains=search)
            | Q(budget__icontains=search)
        )

    if status_filter:
        queryset = queryset.filter(status=status_filter)

    # Unknown values deliberately fall back to the default 24-hour window.
    delta = TIME_FILTERS.get(time_filter, TIME_FILTERS["24h"])
    if delta is not None:
        queryset = queryset.filter(fetched_at__gte=timezone.now() - delta)

    return queryset


class LeadListCreateView(generics.ListCreateAPIView):
    serializer_class = LeadSerializer

    def get_queryset(self):
        search = self.request.query_params.get("search", "").strip()
        status_filter = self.request.query_params.get("status", "").strip()
        time_filter = self.request.query_params.get("time_filter", "24h").strip()
        return filter_jobs(
            Job.objects.all(),
            search=search,
            status_filter=status_filter,
            time_filter=time_filter,
        )

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        total = queryset.count()

        # Pagination
        try:
            page = max(1, int(request.query_params.get("page", 1)))
        except (ValueError, TypeError):
            page = 1

        offset = (page - 1) * PAGE_SIZE
        paginated = queryset[offset: offset + PAGE_SIZE]
        serializer = self.get_serializer(paginated, many=True)

        # Status counts — reuse same filters minus the status filter
        search = request.query_params.get("search", "").strip()
        time_filter = request.query_params.get("time_filter", "24h").strip()
        counts_qs = filter_jobs(Job.objects.all(), search=search, time_filter=time_filter)
        grouped_counts = {
            row["status"]: row["count"]
            for row in counts_qs.values("status").annotate(count=Count("id"))
        }
        status_counts = {lead_status: grouped_counts.get(lead_status, 0) for lead_status in LeadStatus.values}

        return Response(
            {
                "results": serializer.data,
                "total": total,
                "page": page,
                "page_size": PAGE_SIZE,
                "total_pages": max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE),
                "status_counts": status_counts,
            }
        )

    def perform_create(self, serializer):
        job = serializer.save()
        Activity.objects.create(
            activity_type=ActivityType.LEAD_CREATED,
            user=self.request.user,
            job=job,
            description=f"Created job: {job.title}",
        )


class AppliedLeadListView(LeadListCreateView):
    """List only jobs that have been marked as Applied."""

    http_method_names = ["get", "head", "options"]

    def get_queryset(self):
        search = self.request.query_params.get("search", "").strip()
        return filter_jobs(
            Job.objects.filter(status=LeadStatus.APPLIED),
            search=search,
            time_filter="all",
        )


class RejectedLeadListView(APIView):
    """List rejected jobs joined with their rejection reason from rejected_leads."""

    def get(self, request):
        search = request.query_params.get("search", "").strip()

        # Ensure the table exists before querying it.
        _ensure_rejected_leads_table()

        with connection.cursor() as cursor:
            if search:
                cursor.execute(
                    """
                    SELECT j.id, j.title, j.url, j.search_keyword,
                           j.budget, j.budget_min, j.budget_max,
                           j.job_type, j.posted_at, j.fetched_at,
                           j.status, j.skip_reason, j.total_proposals,
                           rl.rejection_reason
                    FROM jobs j
                    LEFT JOIN rejected_leads rl ON rl.id = j.id::text
                    WHERE j.status = 'rejected'
                      AND (j.title ILIKE %s OR j.job_type ILIKE %s OR j.budget ILIKE %s)
                    ORDER BY j.fetched_at DESC
                    """,
                    [f"%{search}%", f"%{search}%", f"%{search}%"],
                )
            else:
                cursor.execute(
                    """
                    SELECT j.id, j.title, j.url, j.search_keyword,
                           j.budget, j.budget_min, j.budget_max,
                           j.job_type, j.posted_at, j.fetched_at,
                           j.status, j.skip_reason, j.total_proposals,
                           rl.rejection_reason
                    FROM jobs j
                    LEFT JOIN rejected_leads rl ON rl.id = j.id::text
                    WHERE j.status = 'rejected'
                    ORDER BY j.fetched_at DESC
                    """
                )
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()

        results = [dict(zip(columns, row)) for row in rows]
        return Response(results)


class LeadDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Job.objects.all()
    serializer_class = LeadSerializer

    def perform_update(self, serializer):
        job = serializer.save()
        Activity.objects.create(
            activity_type=ActivityType.LEAD_UPDATED,
            user=self.request.user,
            job=job,
            description=f"Updated job: {job.title}",
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        title = instance.title
        self.perform_destroy(instance)
        Activity.objects.create(
            activity_type=ActivityType.LEAD_UPDATED,
            user=request.user,
            description=f"Deleted job: {title}",
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class LeadApplyView(APIView):
    """Quickly mark a lead as Applied."""

    def post(self, request, pk):
        # Lock the row so two quick clicks/requests cannot race a status change.
        with transaction.atomic():
            job = get_object_or_404(Job.objects.select_for_update(), pk=pk)
            job.status = LeadStatus.APPLIED
            job.save(update_fields=["status"])
            Activity.objects.create(
                activity_type=ActivityType.APPLIED,
                user=request.user,
                job=job,
                description=f"Marked as applied: {job.title}",
            )
        serializer = LeadSerializer(job)
        return Response(serializer.data)



class LeadRejectView(APIView):
    """Mark a lead as Rejected and record the reason in rejected_leads."""

    def post(self, request, pk):
        job = get_object_or_404(Job, pk=pk)
        rejection_reason = request.data.get("rejection_reason", "").strip()
        if not rejection_reason:
            return Response(
                {"detail": "rejection_reason is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Ensure the table (and title column) exist before we open the
        # main transaction — DDL runs in autocommit so it commits instantly.
        _ensure_rejected_leads_table()

        with transaction.atomic():
            # 1. Update the job status to 'rejected'.
            job_locked = Job.objects.select_for_update().get(pk=pk)
            job_locked.status = LeadStatus.REJECTED
            job_locked.save(update_fields=["status"])

            # 2. Upsert into rejected_leads with title.
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO rejected_leads (id, title, rejection_reason)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (id) DO UPDATE
                        SET title = EXCLUDED.title,
                            rejection_reason = EXCLUDED.rejection_reason
                    """,
                    [str(pk), job_locked.title, rejection_reason],
                )

        return Response({"id": str(pk), "title": job_locked.title, "rejection_reason": rejection_reason})


class LeadAnalysisView(APIView):
    def get(self, request, pk):
        get_object_or_404(Job, pk=pk)

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT score, score_reasoning, tech_stack, proposal_draft
                FROM public.analyses
                WHERE job_id = %s
                """,
                [str(pk)],
            )
            analysis = cursor.fetchone()

        if analysis is None:
            return Response({})

        return Response(
            dict(zip(("score", "score_reasoning", "tech_stack", "proposal_draft"), analysis))
        )

    def patch(self, request, pk):
        get_object_or_404(Job, pk=pk)
        proposal_draft = request.data.get("proposal_draft")

        if proposal_draft is None or not isinstance(proposal_draft, str):
            return Response(
                {"proposal_draft": ["This field is required and must be a string."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE public.analyses
                SET proposal_draft = %s
                WHERE job_id = %s
                RETURNING proposal_draft
                """,
                [proposal_draft, str(pk)],
            )
            updated_proposal = cursor.fetchone()

        if updated_proposal is None:
            return Response(
                {"detail": "No analysis found for this job. Run the AI analysis first."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response({"proposal_draft": updated_proposal[0]})


def _ensure_analyses_tracking_columns():
    """Ensure interviewing, invite_sent, and hired columns exist on public.analyses.

    Runs in autocommit mode so DDL commits immediately.
    """
    with connection.cursor() as cursor:
        old_autocommit = connection.autocommit
        connection.set_autocommit(True)
        try:
            for col, col_type in [
                ("interviewing", "BOOLEAN DEFAULT FALSE"),
                ("invite_sent", "BOOLEAN DEFAULT FALSE"),
                ("hired", "BOOLEAN DEFAULT FALSE"),
                ("proposal_draft", "TEXT"),
            ]:
                try:
                    cursor.execute(
                        f"ALTER TABLE public.analyses ADD COLUMN IF NOT EXISTS {col} {col_type}"
                    )
                except Exception:  # noqa: BLE001
                    pass
        finally:
            connection.set_autocommit(old_autocommit)


class LeadBulkRefreshView(APIView):
    """Refresh proposal, interviewing, invite_sent, and hired for selected jobs.

    POST body: { "ids": ["job-id-1", "job-id-2", ...] }

    Returns:
        A list of job objects with refreshed fields included.
    """

    def post(self, request):
        ids = request.data.get("ids", [])
        if not isinstance(ids, list) or not ids:
            return Response(
                {"detail": "ids must be a non-empty list."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Cap to a sane maximum to avoid accidental full-table scans.
        # These are the primary keys used by the UI and by the jobs/analyses
        # tables.  The refresh service is responsible for converting them to
        # Upwork's ciphertext form for the GraphQL request.
        ids = list(dict.fromkeys(str(i).strip() for i in ids[:500] if str(i).strip()))
        if not ids:
            return Response(
                {"detail": "ids must contain at least one non-empty job ID."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        logger.info("Bulk refresh requested for %d job(s): %s", len(ids), ids)

        # Ensure the tracking columns exist before querying.
        _ensure_analyses_tracking_columns()

        # This call is the actual refresh.  Previously this endpoint only
        # queried analyses, so clicking Refresh could never fetch from Upwork
        # or update the database.
        try:
            from job_refresh.refresh_jobs import refresh_jobs

            summary = refresh_jobs(ids)
        except EnvironmentError as exc:
            logger.error("Bulk refresh configuration error for ids=%s: %s", ids, exc)
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except Exception:  # noqa: BLE001
            logger.exception("Bulk refresh crashed for ids=%s", ids)
            return Response(
                {"detail": "Refresh could not be completed. Check the server logs for details."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        logger.info(
            "Bulk refresh service finished: requested=%d succeeded=%d fetch_failed=%s write_failed=%s",
            len(ids), summary.succeeded, summary.fetch_failed, summary.write_failed,
        )
        if summary.succeeded == 0:
            return Response(
                {"detail": "No selected jobs were refreshed. Check the server logs for the Upwork or database error."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # Fetch fresh analysis data for each requested job.
        with connection.cursor() as cursor:
            placeholders = ",".join(["%s"] * len(ids))
            cursor.execute(
                f"""
                SELECT job_id,
                       COALESCE(proposal_draft, '') AS proposal_draft,
                       COALESCE(interviewing,  FALSE) AS interviewing,
                       COALESCE(invite_sent,   FALSE) AS invite_sent,
                       COALESCE(hired,         FALSE) AS hired
                FROM public.analyses
                WHERE job_id IN ({placeholders})
                """,
                ids,
            )
            rows = cursor.fetchall()

        logger.info("Bulk refresh read-back found %d analyses row(s) for %d requested job(s)", len(rows), len(ids))

        # Build a lookup keyed by job_id.
        analysis_map = {
            row[0]: {
                "proposal_draft": row[1],
                "interviewing": row[2],
                "invite_sent": row[3],
                "hired": row[4],
            }
            for row in rows
        }

        # Load the matching Job rows and merge the refreshed analysis data.
        jobs = Job.objects.filter(id__in=ids)
        serializer = LeadSerializer(jobs, many=True)
        data = serializer.data

        # Overlay the refreshed values onto each serialized job.
        result = []
        for job_data in data:
            analysis = analysis_map.get(str(job_data["id"]), {})
            merged = dict(job_data)
            merged["proposal_draft"] = analysis.get("proposal_draft", "")
            merged["interviewing"] = analysis.get("interviewing", False)
            merged["invite_sent"] = analysis.get("invite_sent", False)
            merged["hired"] = analysis.get("hired", False)
            result.append(merged)

        logger.info("Bulk refresh returning %d refreshed job(s)", len(result))

        return Response(result)
