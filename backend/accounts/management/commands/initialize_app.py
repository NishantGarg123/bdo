"""
Initialize the BDO application: create default admin user and seed sample data.
"""

from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from activity.models import Activity, ActivityType
from integrations.models import Integration, IntegrationStatus
from leads.models import Job, LeadStatus


class Command(BaseCommand):
    help = "Create default admin user and seed sample data for development."

    def handle(self, *args, **options):
        self._create_admin_user()
        admin = User.objects.get(username="admin")
        self._seed_integrations()
        self._seed_jobs()
        self._seed_activities(admin)
        self.stdout.write(self.style.SUCCESS("Application initialized successfully."))

    def _create_admin_user(self):
        if User.objects.filter(username="admin").exists():
            self.stdout.write("Default admin user already exists.")
            return

        User.objects.create_superuser(
            username="admin",
            email="admin@bdo.local",
            password="admin",
        )
        self.stdout.write(self.style.SUCCESS("Created default admin user (admin/admin)."))

    def _seed_integrations(self):
        if Integration.objects.exists():
            self.stdout.write("Integrations already seeded.")
            return

        integrations = [
            ("LinkedIn", "linkedin", "Connect your LinkedIn account for lead sourcing."),
            ("Gmail", "gmail", "Sync emails and track outreach."),
            ("Outlook", "outlook", "Microsoft Outlook email integration."),
            ("Job Portals", "job-portals", "Aggregate leads from job boards."),
            ("ATS Platforms", "ats-platforms", "Connect with applicant tracking systems."),
        ]
        Integration.objects.bulk_create(
            [
                Integration(
                    name=name,
                    slug=slug,
                    description=desc,
                    status=IntegrationStatus.DISCONNECTED,
                )
                for name, slug, desc in integrations
            ]
        )
        self.stdout.write("Seeded integration placeholders.")

    def _seed_jobs(self):
        if Job.objects.exists():
            self.stdout.write("Jobs already seeded.")
            return

        now = timezone.now()
        sample_jobs = [
            {
                "id": "seed-job-1",
                "title": "Senior Full Stack Developer — React & Django",
                "url": "https://example.com/jobs/1",
                "budget": "$5,000 - $8,000",
                "budget_min": 5000,
                "budget_max": 8000,
                "skills": ["React", "Django", "PostgreSQL", "REST API"],
                "job_type": "Fixed Price",
                "posted_at": now - timedelta(days=3),
                "fetched_at": now - timedelta(hours=2),
                "status": LeadStatus.PENDING,
                "total_proposals": 12,
            },
            {
                "id": "seed-job-2",
                "title": "Python Backend Engineer for SaaS Platform",
                "url": "https://example.com/jobs/2",
                "budget": "$60/hr",
                "budget_min": 60,
                "budget_max": 60,
                "skills": ["Python", "FastAPI", "AWS", "Docker"],
                "job_type": "Hourly",
                "posted_at": now - timedelta(days=1),
                "fetched_at": now - timedelta(hours=5),
                "status": LeadStatus.APPLIED,
                "total_proposals": 8,
            },
            {
                "id": "seed-job-3",
                "title": "Mobile App Developer — React Native",
                "url": "https://example.com/jobs/3",
                "budget": "$3,000",
                "budget_min": 3000,
                "budget_max": 3000,
                "skills": ["React Native", "TypeScript", "Firebase"],
                "job_type": "Fixed Price",
                "posted_at": now - timedelta(days=7),
                "fetched_at": now - timedelta(days=2),
                "status": LeadStatus.REJECTED,
                "total_proposals": 25,
            },
            {
                "id": "seed-job-4",
                "title": "DevOps Engineer — CI/CD Pipeline Setup",
                "url": "https://example.com/jobs/4",
                "budget": "$4,000 - $6,000",
                "budget_min": 4000,
                "budget_max": 6000,
                "skills": ["Docker", "Kubernetes", "GitHub Actions", "Terraform"],
                "job_type": "Fixed Price",
                "posted_at": now - timedelta(days=2),
                "fetched_at": now - timedelta(hours=12),
                "status": LeadStatus.PENDING,
                "total_proposals": 5,
            },
            {
                "id": "seed-job-5",
                "title": "Data Analyst — Power BI Dashboard",
                "url": "https://example.com/jobs/5",
                "budget": "$45/hr",
                "budget_min": 45,
                "budget_max": 45,
                "skills": ["Power BI", "SQL", "Excel", "Python"],
                "job_type": "Hourly",
                "posted_at": now - timedelta(days=5),
                "fetched_at": now - timedelta(days=1),
                "status": LeadStatus.SKIPPED,
                "skip_reason": "Budget below minimum threshold",
                "total_proposals": 18,
            },
            {
                "id": "seed-job-6",
                "title": "UI/UX Designer for E-commerce Redesign",
                "url": "https://example.com/jobs/6",
                "budget": "$2,500",
                "budget_min": 2500,
                "budget_max": 2500,
                "skills": ["Figma", "UI Design", "Prototyping"],
                "job_type": "Fixed Price",
                "posted_at": now - timedelta(hours=18),
                "fetched_at": now - timedelta(hours=1),
                "status": LeadStatus.IN_PROGRESS,
                "total_proposals": 3,
            },
            {
                "id": "seed-job-7",
                "title": "Machine Learning Engineer — NLP Project",
                "url": "https://example.com/jobs/7",
                "budget": "$10,000+",
                "budget_min": 10000,
                "budget_max": 15000,
                "skills": ["Python", "PyTorch", "NLP", "Transformers"],
                "job_type": "Fixed Price",
                "posted_at": now - timedelta(days=4),
                "fetched_at": now - timedelta(hours=8),
                "status": LeadStatus.PENDING,
                "total_proposals": 7,
            },
            {
                "id": "seed-job-8",
                "title": "WordPress Developer — Custom Theme",
                "url": "https://example.com/jobs/8",
                "budget": "$1,500",
                "budget_min": 1500,
                "budget_max": 1500,
                "skills": ["WordPress", "PHP", "CSS", "JavaScript"],
                "job_type": "Fixed Price",
                "posted_at": now - timedelta(days=10),
                "fetched_at": now - timedelta(days=3),
                "status": LeadStatus.APPLIED,
                "total_proposals": 30,
            },
        ]

        Job.objects.bulk_create([Job(**data) for data in sample_jobs])
        self.stdout.write("Seeded sample jobs.")

    def _seed_activities(self, admin):
        if Activity.objects.exists():
            self.stdout.write("Activities already seeded.")
            return

        now = timezone.now()
        jobs = list(Job.objects.all()[:5])
        activity_data = [
            (ActivityType.LEAD_CREATED, "Created new job", 1),
            (ActivityType.LEAD_UPDATED, "Updated job details", 3),
            (ActivityType.APPLIED, "Applied to company via portal", 5),
            (ActivityType.NOTES_ADDED, "Added follow-up notes", 2),
            (ActivityType.STATUS_CHANGED, "Changed status to Applied", 7),
            (ActivityType.LEAD_CREATED, "Created new job", 0),
            (ActivityType.APPLIED, "Submitted application", 10),
            (ActivityType.NOTES_ADDED, "Added interview prep notes", 4),
        ]

        for i, (atype, desc, hours_ago) in enumerate(activity_data):
            job = jobs[i % len(jobs)] if jobs else None
            activity = Activity.objects.create(
                activity_type=atype,
                user=admin,
                job=job,
                description=desc,
            )
            Activity.objects.filter(pk=activity.pk).update(
                created_at=now - timedelta(hours=hours_ago)
            )

        self.stdout.write("Seeded sample activities.")
