"""
Activity model — audit trail for job-related actions.

Future enhancements: notifications, analytics, filtering by type/user.
"""

from django.conf import settings
from django.db import models

from leads.models import Job


class ActivityType(models.TextChoices):
    LEAD_CREATED = "lead_created", "Lead Created"
    LEAD_UPDATED = "lead_updated", "Lead Updated"
    APPLIED = "applied", "Applied to Company"
    NOTES_ADDED = "notes_added", "Notes Added"
    STATUS_CHANGED = "status_changed", "Status Changed"


class Activity(models.Model):
    activity_type = models.CharField(max_length=30, choices=ActivityType.choices)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="activities",
    )
    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="activities",
    )
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "activities"

    def __str__(self):
        return f"{self.get_activity_type_display()} by {self.user}"
