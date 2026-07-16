"""Migration state for the externally managed ``public.jobs`` table.

The jobs table is provisioned by the application's database, not by Django.
Keeping this state-only migration lets Django resolve relations to Job without
creating, renaming, or altering the externally managed table.
"""

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name="Job",
                    fields=[
                        ("id", models.CharField(max_length=255, primary_key=True, serialize=False)),
                        ("title", models.CharField(max_length=500)),
                        ("description", models.TextField(blank=True, null=True)),
                        ("url", models.URLField(blank=True, default="", max_length=1000)),
                        ("budget", models.CharField(blank=True, default="", max_length=100)),
                        ("budget_min", models.FloatField(blank=True, null=True)),
                        ("budget_max", models.FloatField(blank=True, null=True)),
                        ("skills", models.JSONField(blank=True, default=list)),
                        ("job_type", models.CharField(blank=True, default="", max_length=100)),
                        ("posted_at", models.DateTimeField(blank=True, null=True)),
                        ("fetched_at", models.DateTimeField(default=django.utils.timezone.now)),
                        (
                            "status",
                            models.CharField(
                                choices=[
                                    ("pending", "Pending"),
                                    ("applied", "Applied"),
                                    ("rejected", "Rejected"),
                                    ("skipped", "Skipped"),
                                    ("in_progress", "In Progress"),
                                ],
                                default="pending",
                                max_length=20,
                            ),
                        ),
                        ("skip_reason", models.CharField(blank=True, default="", max_length=500)),
                        ("total_proposals", models.IntegerField(default=0)),
                    ],
                    options={"db_table": "jobs", "ordering": ["-fetched_at"]},
                ),
            ],
        ),
    ]
