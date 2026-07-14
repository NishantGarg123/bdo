from datetime import datetime, timezone

from django.db import migrations


DEFAULT_LEADS = [
    {
        "id": 2067611184842837150,
        "title": "Appointment Setter / Lead Manager (Instantly, Heyreach, GHL)",
        "url": "https://www.upwork.com/jobs/~022067611184842837150",
        "budget": "$10-$20/hr",
        "budget_min": 10.0,
        "budget_max": 20.0,
        "skills": [],
        "job_type": "hourly",
        "posted_at": datetime(2026, 6, 18, 14, 13, 54, tzinfo=timezone.utc),
        "fetched_at": datetime(2026, 6, 18, 14, 14, 12, 40194, tzinfo=timezone.utc),
        "status": "skipped",
        "skip_reason": "not a tech/software job",
        "total_proposals": 0,
    },
    {
        "id": 2067611139554049199,
        "title": "Star Wars Thumbnail Creator",
        "url": "https://www.upwork.com/jobs/~022067611139554049199",
        "budget": "$10-$20/hr",
        "budget_min": 10.0,
        "budget_max": 20.0,
        "skills": [],
        "job_type": "hourly",
        "posted_at": datetime(2026, 6, 18, 14, 13, 53, tzinfo=timezone.utc),
        "fetched_at": datetime(2026, 6, 18, 14, 14, 12, 44616, tzinfo=timezone.utc),
        "status": "skipped",
        "skip_reason": "hourly rate too low ($10-$20/hr)",
        "total_proposals": 0,
    },
    {
        "id": 2067611206679528770,
        "title": "WordPress Optimization & AI Lead Specialist",
        "url": "https://www.upwork.com/jobs/~022067611206679528770",
        "budget": "$100.0",
        "budget_min": 100.0,
        "budget_max": 100.0,
        "skills": [],
        "job_type": "fixed",
        "posted_at": datetime(2026, 6, 18, 14, 13, 39, tzinfo=timezone.utc),
        "fetched_at": datetime(2026, 6, 18, 14, 14, 12, 48242, tzinfo=timezone.utc),
        "status": "skipped",
        "skip_reason": "fixed budget too low ($100.0)",
        "total_proposals": 0,
    },
]


def seed_default_leads(apps, schema_editor):
    Lead = apps.get_model("leads", "Lead")

    for lead in DEFAULT_LEADS:
        lead_id = lead["id"]
        Lead.objects.update_or_create(
            id=lead_id,
            defaults={key: value for key, value in lead.items() if key != "id"},
        )


class Migration(migrations.Migration):
    dependencies = [
        ("leads", "0002_align_legacy_leads_table"),
    ]

    operations = [
        migrations.RunPython(seed_default_leads, migrations.RunPython.noop),
    ]
