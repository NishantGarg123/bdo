from django.contrib import admin

from .models import Integration


@admin.register(Integration)
class IntegrationAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "status", "updated_at"]
    list_filter = ["status"]
