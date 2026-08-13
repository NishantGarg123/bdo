from django.contrib import admin

from .models import Activity


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ["activity_type", "user", "job", "created_at"]
    list_filter = ["activity_type", "created_at"]
