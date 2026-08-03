"""Keep Django's Job status choices aligned with the externally managed table."""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("leads", "0001_initial")]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AlterField(
                    model_name="job",
                    name="status",
                    field=models.CharField(
                        choices=[
                            ("analyzed", "Analyzed"),
                            ("pending", "Pending"),
                            ("applied", "Applied"),
                            ("rejected", "Rejected"),
                            ("skipped", "Skipped"),
                            ("in_progress", "In Progress"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                )
            ],
        )
    ]
