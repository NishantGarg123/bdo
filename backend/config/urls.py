"""
Root URL configuration for BDO Lead Management API.
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("accounts.urls")),
    path("api/", include("dashboard.urls")),
    path("api/", include("leads.urls")),
    path("api/", include("activity.urls")),
    path("api/", include("integrations.urls")),
]
