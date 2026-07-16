"""
Job model — core entity for BDO lead management.

Backed by the externally managed public.jobs table with a text primary key.

Future enhancements: assignment, comments, resume uploads, AI recommendations.
"""

from django.db import models
from django.utils import timezone


class LeadStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPLIED = "applied", "Applied"
    REJECTED = "rejected", "Rejected"
    SKIPPED = "skipped", "Skipped"
    IN_PROGRESS = "in_progress", "In Progress"


class Job(models.Model):
    id = models.CharField(primary_key=True, max_length=255)
    title = models.CharField(max_length=500)
    description = models.TextField(null=True, blank=True)
    url = models.URLField(max_length=1000, blank=True, default="")
    budget = models.CharField(max_length=100, blank=True, default="")
    budget_min = models.FloatField(null=True, blank=True)
    budget_max = models.FloatField(null=True, blank=True)
    skills = models.JSONField(default=list, blank=True)
    job_type = models.CharField(max_length=100, blank=True, default="")
    posted_at = models.DateTimeField(null=True, blank=True)
    fetched_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(
        max_length=20,
        choices=LeadStatus.choices,
        default=LeadStatus.PENDING,
    )
    skip_reason = models.CharField(max_length=500, blank=True, default="")
    total_proposals = models.IntegerField(default=0)

    class Meta:
        db_table = "jobs"
        ordering = ["-fetched_at"]

    def __str__(self):
        return self.title
