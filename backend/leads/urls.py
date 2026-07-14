from django.urls import path

from .views import LeadAnalysisView, LeadDetailView, LeadListCreateView

urlpatterns = [
    path("leads/", LeadListCreateView.as_view(), name="lead-list"),
    path("leads/<int:pk>/analysis/", LeadAnalysisView.as_view(), name="lead-analysis"),
    path("leads/<int:pk>/", LeadDetailView.as_view(), name="lead-detail"),
]
