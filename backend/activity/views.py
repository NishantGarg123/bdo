"""
Activity serializers and views.
"""

from rest_framework import serializers
from rest_framework.generics import ListAPIView

from .models import Activity


class ActivitySerializer(serializers.ModelSerializer):
    activity_type_display = serializers.CharField(
        source="get_activity_type_display",
        read_only=True,
    )
    username = serializers.CharField(source="user.username", read_only=True)
    lead_title = serializers.CharField(source="lead.title", read_only=True)

    class Meta:
        model = Activity
        fields = [
            "id",
            "activity_type",
            "activity_type_display",
            "username",
            "description",
            "lead_title",
            "created_at",
        ]


class ActivityListView(ListAPIView):
    serializer_class = ActivitySerializer
    queryset = Activity.objects.select_related("user", "lead").all()
