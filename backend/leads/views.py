"""
Lead API views — list, create, retrieve, update, delete.
"""

from django.db.models import Q
from rest_framework import generics, status
from rest_framework.response import Response

from activity.models import Activity, ActivityType

from .models import Lead
from .serializers import LeadSerializer


class LeadListCreateView(generics.ListCreateAPIView):
    serializer_class = LeadSerializer

    def get_queryset(self):
        queryset = Lead.objects.all()
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
        lead = serializer.save()
        Activity.objects.create(
            activity_type=ActivityType.LEAD_CREATED,
            user=self.request.user,
            lead=lead,
            description=f"Created lead: {lead.title}",
        )


class LeadDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Lead.objects.all()
    serializer_class = LeadSerializer

    def perform_update(self, serializer):
        lead = serializer.save()
        Activity.objects.create(
            activity_type=ActivityType.LEAD_UPDATED,
            user=self.request.user,
            lead=lead,
            description=f"Updated lead: {lead.title}",
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        title = instance.title
        self.perform_destroy(instance)
        Activity.objects.create(
            activity_type=ActivityType.LEAD_UPDATED,
            user=request.user,
            description=f"Deleted lead: {title}",
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
