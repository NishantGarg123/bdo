"""
Job serializers.
"""

from rest_framework import serializers

from .models import Job


class LeadSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    # These three fields live in public.analyses, not in the jobs table.
    # The list view provides persisted values from public.analyses in context.
    interviewing = serializers.SerializerMethodField()
    interview_count = serializers.SerializerMethodField()
    invite_sent = serializers.SerializerMethodField()
    hired = serializers.SerializerMethodField()

    class Meta:
        model = Job
        fields = [
            "id",
            "title",
            "description",
            "url",
            "search_keyword",
            "budget",
            "budget_min",
            "budget_max",
            "skills",
            "job_type",
            "posted_at",
            "fetched_at",
            "status",
            "status_display",
            "skip_reason",
            "total_proposals",
            "interviewing",
            "interview_count",
            "invite_sent",
            "hired",
        ]

    def get_interviewing(self, obj):
        return self.context.get("tracking_by_job_id", {}).get(str(obj.id), {}).get("interviewing", False)

    def get_interview_count(self, obj):
        return self.context.get("tracking_by_job_id", {}).get(str(obj.id), {}).get("interview_count", 0)

    def get_invite_sent(self, obj):
        return self.context.get("tracking_by_job_id", {}).get(str(obj.id), {}).get("invite_sent", 0)

    def get_hired(self, obj):
        return self.context.get("tracking_by_job_id", {}).get(str(obj.id), {}).get("hired", False)

    def validate_skills(self, value):
        if value is None:
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError("Skills must be a list of strings.")
        return [str(skill).strip() for skill in value if str(skill).strip()]
