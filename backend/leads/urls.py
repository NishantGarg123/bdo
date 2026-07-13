from django.urls import path

from .views import LeadDetailView, LeadListCreateView

urlpatterns = [
    path("leads/", LeadListCreateView.as_view(), name="lead-list"),
    path("leads/<int:pk>/", LeadDetailView.as_view(), name="lead-detail"),
]
