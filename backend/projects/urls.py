from django.urls import path

from .views import FAQDetailView, FAQListCreateView, KnowledgeBaseListView, IssueDetailView, IssueListCreateView, ProjectDetailView, ProjectListCreateView

urlpatterns = [
    path("projects/", ProjectListCreateView.as_view(), name="project-list"),
    path("projects/<int:pk>/", ProjectDetailView.as_view(), name="project-detail"),
    path("projects/<int:project_pk>/issues/", IssueListCreateView.as_view(), name="project-issue-list"),
    path("projects/<int:project_pk>/faqs/", FAQListCreateView.as_view(), name="project-faq-list"),
    path("issues/<int:pk>/", IssueDetailView.as_view(), name="issue-detail"),
    path("faqs/<int:pk>/", FAQDetailView.as_view(), name="faq-detail"),
    path("knowledge-base/", KnowledgeBaseListView.as_view(), name="knowledge-base"),
]

