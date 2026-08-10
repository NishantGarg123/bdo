from django.conf import settings
from django.db import models


class IssueStatus(models.TextChoices):
    OPEN = "open", "Open"
    NOT_RESOLVED = "not_resolved", "Not Resolved"
    RESOLVED = "resolved", "Resolved"


class Project(models.Model):
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="projects")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.name


class ProjectIssue(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="issues")
    title = models.CharField(max_length=240)
    description = models.TextField()
    investigation = models.TextField(blank=True)
    root_cause = models.TextField(blank=True)
    solution = models.TextField(blank=True)
    technical_notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=IssueStatus.choices, default=IssueStatus.OPEN)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="project_issues")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.title
