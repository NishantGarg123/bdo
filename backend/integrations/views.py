"""
Integration serializers and views.
"""

from rest_framework import serializers
from rest_framework.generics import ListAPIView

from .models import Integration


class IntegrationSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Integration
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "status",
            "status_display",
        ]


class IntegrationListView(ListAPIView):
    serializer_class = IntegrationSerializer
    queryset = Integration.objects.all()
