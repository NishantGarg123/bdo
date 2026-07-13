from django.urls import path

from .views import IntegrationListView

urlpatterns = [
    path("integrations/", IntegrationListView.as_view(), name="integration-list"),
]
