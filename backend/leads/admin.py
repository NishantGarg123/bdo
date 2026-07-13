from django.contrib import admin

from .models import Lead


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "job_type",
        "status",
        "budget",
        "total_proposals",
        "fetched_at",
    ]
    list_filter = ["status", "job_type", "fetched_at"]
    search_fields = ["title", "job_type", "budget", "skills"]
