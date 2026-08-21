"""
Management command to sync all existing ProjectFAQs to Pinecone.

Usage:
    python manage.py sync_faqs_pinecone
    python manage.py sync_faqs_pinecone --project-id=3
"""

from django.core.management.base import BaseCommand

from projects.models import ProjectFAQ
from projects.vector_service import upsert_faq_to_pinecone


class Command(BaseCommand):
    help = "Backfill / re-index all Project FAQs into the Pinecone vector store."

    def add_arguments(self, parser):
        parser.add_argument(
            "--project-id",
            type=int,
            default=None,
            help="Only sync FAQs for a specific project ID.",
        )

    def handle(self, *args, **options):
        qs = ProjectFAQ.objects.select_related("project").all()
        project_id = options.get("project_id")
        if project_id:
            qs = qs.filter(project_id=project_id)
            self.stdout.write(f"Syncing FAQs for project {project_id}...")
        else:
            self.stdout.write("Syncing ALL FAQs to Pinecone...")

        total = qs.count()
        success = 0
        failed = 0

        for faq in qs:
            try:
                doc_id = upsert_faq_to_pinecone(faq)
                if doc_id != faq.pinecone_doc_id:
                    faq.pinecone_doc_id = doc_id
                    faq.save(update_fields=["pinecone_doc_id"])
                success += 1
                self.stdout.write(f"  [OK]  FAQ #{faq.id} -> {doc_id}")
            except Exception as exc:
                failed += 1
                self.stderr.write(f"  [ERR] FAQ #{faq.id}: {exc}")

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone! {success}/{total} synced successfully, {failed} failed."
            )
        )
