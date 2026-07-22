"""
Job API views — list, create, retrieve, update, delete.
"""

from datetime import timedelta

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
