"""
Lead serializers.
"""

from rest_framework import serializers

from .models import Lead


class LeadSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Lead
        fields = [
            "id",
            "title",
            "url",
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
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def validate_skills(self, value):
        if value is None:
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError("Skills must be a list of strings.")
        return [str(skill).strip() for skill in value if str(skill).strip()]
