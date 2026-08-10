from django.urls import path

from .views import KnowledgeBaseListView, IssueDetailView, IssueListCreateView, ProjectDetailView, ProjectListCreateView

urlpatterns = [
    path("projects/", ProjectListCreateView.as_view(), name="project-list"),
    path("projects/<int:pk>/", ProjectDetailView.as_view(), name="project-detail"),
    path("projects/<int:project_pk>/issues/", IssueListCreateView.as_view(), name="project-issue-list"),
    path("issues/<int:pk>/", IssueDetailView.as_view(), name="issue-detail"),
    path("knowledge-base/", KnowledgeBaseListView.as_view(), name="knowledge-base"),
]
