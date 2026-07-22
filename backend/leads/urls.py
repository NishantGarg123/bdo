from django.urls import path

from .views import AppliedLeadListView, LeadAnalysisView, LeadApplyView, LeadDetailView, LeadListCreateView

urlpatterns = [
    path("leads/", LeadListCreateView.as_view(), name="lead-list"),
    path("leads/applied/", AppliedLeadListView.as_view(), name="applied-lead-list"),
    path("leads/<str:pk>/apply/", LeadApplyView.as_view(), name="lead-apply"),
    path("leads/<str:pk>/analysis/", LeadAnalysisView.as_view(), name="lead-analysis"),
    path("leads/<str:pk>/", LeadDetailView.as_view(), name="lead-detail"),
]
