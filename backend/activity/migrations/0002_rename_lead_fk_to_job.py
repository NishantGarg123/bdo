"""
Migration 0002: Rename Activity.lead FK → Activity.job.

Idempotent — only renames lead_id → job_id if lead_id still exists.
Django state always reflects the new field name 'job'.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("activity", "0001_initial"),
        ("leads", "0006_rename_leads_lead_to_jobs"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
                    DO $$
                    BEGIN
                        -- Only rename if lead_id column still exists
                        IF EXISTS (
                            SELECT 1 FROM information_schema.columns
                            WHERE table_schema = 'public'
                              AND table_name   = 'activity_activity'
                              AND column_name  = 'lead_id'
                        ) THEN
                            ALTER TABLE activity_activity RENAME COLUMN lead_id TO job_id;
                        END IF;
                    END $$;
                    """,
                    reverse_sql="""
                    DO $$
                    BEGIN
                        IF EXISTS (
                            SELECT 1 FROM information_schema.columns
                            WHERE table_schema = 'public'
                              AND table_name   = 'activity_activity'
                              AND column_name  = 'job_id'
                        ) THEN
                            ALTER TABLE activity_activity RENAME COLUMN job_id TO lead_id;
                        END IF;
                    END $$;
                    """,
                ),
            ],
            state_operations=[
                migrations.RenameField(
                    model_name="Activity",
                    old_name="lead",
                    new_name="job",
                ),
            ],
        ),
    ]
