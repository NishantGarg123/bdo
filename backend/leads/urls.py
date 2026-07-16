from django.urls import path

from .views import LeadAnalysisView, LeadDetailView, LeadListCreateView

urlpatterns = [
    path("leads/", LeadListCreateView.as_view(), name="lead-list"),
    path("leads/<str:pk>/analysis/", LeadAnalysisView.as_view(), name="lead-analysis"),
    path("leads/<str:pk>/", LeadDetailView.as_view(), name="lead-detail"),
]
