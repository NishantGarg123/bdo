"""
Job API views — list, create, retrieve, update, delete.
"""

from django.db import connection
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from activity.models import Activity, ActivityType

from .models import Job
from .serializers import LeadSerializer


class LeadListCreateView(generics.ListCreateAPIView):
    serializer_class = LeadSerializer

    def get_queryset(self):
        queryset = Job.objects.all()
        search = self.request.query_params.get("search", "").strip()
        status_filter = self.request.query_params.get("status", "").strip()

        if search:
            queryset = queryset.filter(
                Q(title__icontains=search)
                | Q(job_type__icontains=search)
                | Q(budget__icontains=search)
            )

        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset

    def perform_create(self, serializer):
        job = serializer.save()
        Activity.objects.create(
            activity_type=ActivityType.LEAD_CREATED,
            user=self.request.user,
            job=job,
            description=f"Created job: {job.title}",
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
