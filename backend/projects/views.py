from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

import logging

from .models import Project, ProjectIssue, ProjectFAQ, IssueStatus
from .serializers import ProjectSerializer, ProjectIssueSerializer, ProjectFAQSerializer
from .vector_service import (
    upsert_faq_to_pinecone,
    delete_faq_from_pinecone,
    query_project_faqs,
    generate_agent_answer,
)

logger = logging.getLogger(__name__)


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
        faq = serializer.save(project=self.get_project())
        # Sync to Pinecone
        try:
            doc_id = upsert_faq_to_pinecone(faq)
            faq.pinecone_doc_id = doc_id
            faq.save(update_fields=["pinecone_doc_id"])
        except Exception:
            logger.exception("Failed to upsert FAQ %s to Pinecone on create", faq.id)


class FAQDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ProjectFAQSerializer

    def get_queryset(self):
        return ProjectFAQ.objects.all()

    def perform_update(self, serializer):
        faq = serializer.save()
        # Re-sync updated FAQ to Pinecone
        try:
            doc_id = upsert_faq_to_pinecone(faq)
            if doc_id != faq.pinecone_doc_id:
                faq.pinecone_doc_id = doc_id
                faq.save(update_fields=["pinecone_doc_id"])
        except Exception:
            logger.exception("Failed to upsert FAQ %s to Pinecone on update", faq.id)

    def perform_destroy(self, instance):
        # Delete from Pinecone first, then SQL
        try:
            delete_faq_from_pinecone(instance.pinecone_doc_id)
        except Exception:
            logger.exception("Failed to delete FAQ %s from Pinecone", instance.id)
        instance.delete()


class ProjectAgentChatView(APIView):
    """
    POST /api/projects/agent/chat/

    Accepts: {"project_id": int, "question": str, "history": [...]}
    Returns: {"answer": str, "sources": [...]}
    """

    def post(self, request):
        project_id = request.data.get("project_id")
        question = request.data.get("question", "").strip()
        history = request.data.get("history", [])

        if not project_id or not question:
            return Response(
                {"detail": "Both 'project_id' and 'question' are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        project = get_object_or_404(Project, pk=project_id)

        try:
            # 1. Similarity search
            retrieved_faqs = query_project_faqs(project_id, question, top_k=5)

            # 2. Generate grounded answer
            result = generate_agent_answer(
                project_name=project.name,
                question=question,
                retrieved_faqs=retrieved_faqs,
                chat_history=history if history else None,
            )

            return Response(result)
        except Exception:
            logger.exception("Agent chat failed for project %s", project_id)
            return Response(
                {"detail": "An error occurred while processing your question. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
