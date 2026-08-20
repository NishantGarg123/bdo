from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework import generics

from .models import Project, ProjectIssue, ProjectFAQ, IssueStatus
from .serializers import ProjectSerializer, ProjectIssueSerializer, ProjectFAQSerializer


def projects_queryset():
    return Project.objects.annotate(
        issue_count=Count("issues"),
        open_issue_count=Count("issues", filter=Q(issues__status=IssueStatus.OPEN)),
        resolved_issue_count=Count("issues", filter=Q(issues__status=IssueStatus.RESOLVED)),
    )


class ProjectListCreateView(generics.ListCreateAPIView):
    serializer_class = ProjectSerializer

    def get_queryset(self):
        search = self.request.query_params.get("search", "").strip()
        queryset = projects_queryset()
        return queryset.filter(Q(name__icontains=search) | Q(description__icontains=search)) if search else queryset

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class ProjectDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ProjectSerializer

    def get_queryset(self):
        return projects_queryset()


class IssueListCreateView(generics.ListCreateAPIView):
    serializer_class = ProjectIssueSerializer

    def get_project(self):
        return get_object_or_404(Project, pk=self.kwargs["project_pk"])

    def get_queryset(self):
        queryset = ProjectIssue.objects.filter(project=self.get_project()).select_related("project", "created_by")
        status = self.request.query_params.get("status", "").strip()
        search = self.request.query_params.get("search", "").strip()
        if status:
            queryset = queryset.filter(status=status)
        if search:
            queryset = queryset.filter(Q(title__icontains=search) | Q(description__icontains=search) | Q(solution__icontains=search))
        return queryset

    def perform_create(self, serializer):
        serializer.save(project=self.get_project(), created_by=self.request.user)


class IssueDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ProjectIssueSerializer

    def get_queryset(self):
        return ProjectIssue.objects.select_related("project", "created_by")


class KnowledgeBaseListView(generics.ListAPIView):
    serializer_class = ProjectIssueSerializer

    def get_queryset(self):
        queryset = ProjectIssue.objects.filter(status=IssueStatus.RESOLVED).exclude(solution="").select_related("project", "created_by")
        search = self.request.query_params.get("search", "").strip()
        project_id = self.request.query_params.get("project", "").strip()
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        if search:
            queryset = queryset.filter(Q(title__icontains=search) | Q(description__icontains=search) | Q(root_cause__icontains=search) | Q(solution__icontains=search) | Q(technical_notes__icontains=search))
        return queryset


class FAQListCreateView(generics.ListCreateAPIView):
    serializer_class = ProjectFAQSerializer

    def get_project(self):
        return get_object_or_404(Project, pk=self.kwargs["project_pk"])

    def get_queryset(self):
        return ProjectFAQ.objects.filter(project=self.get_project())

    def perform_create(self, serializer):
        serializer.save(project=self.get_project())


class FAQDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ProjectFAQSerializer

    def get_queryset(self):
        return ProjectFAQ.objects.all()
