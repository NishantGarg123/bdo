from rest_framework import serializers

from .models import Project, ProjectIssue, IssueStatus


class ProjectIssueSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    project_name = serializers.CharField(source="project.name", read_only=True)
    created_by_name = serializers.CharField(source="created_by.username", read_only=True)

    class Meta:
        model = ProjectIssue
        fields = ["id", "project", "project_name", "title", "description", "investigation", "root_cause", "solution", "technical_notes", "status", "status_display", "created_by_name", "created_at", "updated_at"]
        read_only_fields = ["project"]

    def validate(self, attrs):
        status = attrs.get("status", getattr(self.instance, "status", IssueStatus.OPEN))
        solution = attrs.get("solution", getattr(self.instance, "solution", ""))
        if status == IssueStatus.RESOLVED and not solution.strip():
            raise serializers.ValidationError({"solution": "A documented solution is required before resolving an issue."})
        return attrs


class ProjectSerializer(serializers.ModelSerializer):
    issue_count = serializers.IntegerField(read_only=True)
    open_issue_count = serializers.IntegerField(read_only=True)
    resolved_issue_count = serializers.IntegerField(read_only=True)
    health = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ["id", "name", "description", "issue_count", "open_issue_count", "resolved_issue_count", "health", "created_at", "updated_at"]

    def get_health(self, obj):
        open_count = getattr(obj, "open_issue_count", 0)
        unresolved = getattr(obj, "issue_count", 0) - getattr(obj, "resolved_issue_count", 0)
        if open_count == 0 and unresolved == 0:
            return "healthy"
        if unresolved >= 3:
            return "attention"
        return "monitoring"
