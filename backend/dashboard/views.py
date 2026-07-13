"""
Dashboard API — aggregate lead statistics.

Future enhancements: charts, date ranges, user-specific metrics.
"""

from django.db.models import Count
from rest_framework.response import Response
from rest_framework.views import APIView

from leads.models import Lead, LeadStatus


class DashboardView(APIView):
    def get(self, request):
        status_counts = (
            Lead.objects.values("status")
            .annotate(count=Count("id"))
            .order_by("status")
        )
        counts_map = {item["status"]: item["count"] for item in status_counts}
        total = sum(counts_map.values())

        return Response(
            {
                "total_leads": total,
                "pending_leads": counts_map.get(LeadStatus.PENDING, 0),
                "applied_leads": counts_map.get(LeadStatus.APPLIED, 0),
                "rejected_leads": counts_map.get(LeadStatus.REJECTED, 0),
                "skipped_leads": counts_map.get(LeadStatus.SKIPPED, 0),
                "in_progress_leads": counts_map.get(LeadStatus.IN_PROGRESS, 0),
                # Kept for backward compatibility with dashboard UI label
                "new_leads": counts_map.get(LeadStatus.PENDING, 0),
            }
        )
