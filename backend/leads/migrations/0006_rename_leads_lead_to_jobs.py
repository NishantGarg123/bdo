"""
Migration 0006: Ensure jobs table exists with the correct schema.

Fully idempotent — safe to run regardless of DB state:
  - If leads_lead exists: rename it to jobs and update schema.
  - If jobs already exists: skip the rename, just ensure columns are correct.
  - If neither exists: create jobs from scratch.

Also updates analyses table: lead_id → job_id.
"""

from django.db import migrations, models


IDEMPOTENT_JOBS_SCHEMA = """
DO $$
BEGIN

    -- ----------------------------------------------------------------
    -- STEP 0: Drop the old FK constraint if it exists
    -- ----------------------------------------------------------------
    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'activity_activity_lead_id_c6d2b0ea_fk_leads_lead_id'
          AND table_name = 'activity_activity'
    ) THEN
        ALTER TABLE activity_activity
            DROP CONSTRAINT activity_activity_lead_id_c6d2b0ea_fk_leads_lead_id;
    END IF;

    -- ----------------------------------------------------------------
    -- STEP 1: Get jobs table into existence
    -- ----------------------------------------------------------------
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'jobs'
    ) THEN
        IF EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = 'leads_lead'
        ) THEN
            -- Rename leads_lead → jobs
            ALTER TABLE leads_lead RENAME TO jobs;
        ELSE
            -- Create jobs from scratch (fresh cloud DB)
            CREATE TABLE public.jobs (
                id          text PRIMARY KEY,
                title       text NOT NULL,
                description text,
                url         text NOT NULL DEFAULT '',
                budget      text NOT NULL DEFAULT '',
                budget_min  double precision,
                budget_max  double precision,
                skills      jsonb NOT NULL DEFAULT '[]'::jsonb,
                job_type    text NOT NULL DEFAULT '',
                posted_at   timestamp with time zone,
                fetched_at  timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
                status      text NOT NULL DEFAULT 'pending',
                skip_reason text NOT NULL DEFAULT '',
                total_proposals integer NOT NULL DEFAULT 0
            );
        END IF;
    END IF;

    -- ----------------------------------------------------------------
    -- STEP 2: Ensure id column is text (if it was bigint from rename)
    -- ----------------------------------------------------------------
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name   = 'jobs'
          AND column_name  = 'id'
          AND data_type    IN ('bigint', 'integer', 'smallint')
    ) THEN
        -- Drop identity/sequence so we can change the type
        BEGIN
            ALTER TABLE jobs ALTER COLUMN id DROP IDENTITY;
        EXCEPTION WHEN others THEN NULL;
        END;
        ALTER TABLE jobs ALTER COLUMN id DROP DEFAULT;
        ALTER TABLE jobs ALTER COLUMN id TYPE text USING id::text;
    END IF;

    -- ----------------------------------------------------------------
    -- STEP 3: Add description column if missing
    -- ----------------------------------------------------------------
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name   = 'jobs'
          AND column_name  = 'description'
    ) THEN
        ALTER TABLE jobs ADD COLUMN description text;
    END IF;

    -- ----------------------------------------------------------------
    -- STEP 4: Drop Django-managed columns not in new schema
    -- ----------------------------------------------------------------
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name   = 'jobs'
          AND column_name  = 'created_at'
    ) THEN
        ALTER TABLE jobs DROP COLUMN created_at;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name   = 'jobs'
          AND column_name  = 'updated_at'
    ) THEN
        ALTER TABLE jobs DROP COLUMN updated_at;
    END IF;

    -- ----------------------------------------------------------------
    -- STEP 5: Fix activity_activity.lead_id column
    --   a) Cast to text if still bigint
    --   b) Rename to job_id if still called lead_id
    -- ----------------------------------------------------------------
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name   = 'activity_activity'
          AND column_name  = 'lead_id'
          AND data_type    IN ('bigint', 'integer', 'smallint')
    ) THEN
        ALTER TABLE activity_activity ALTER COLUMN lead_id TYPE text USING lead_id::text;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name   = 'activity_activity'
          AND column_name  = 'lead_id'
    ) THEN
        ALTER TABLE activity_activity RENAME COLUMN lead_id TO job_id;
    END IF;

    -- ----------------------------------------------------------------
    -- STEP 6: analyses table — rename lead_id → job_id if needed
    -- ----------------------------------------------------------------
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'analyses'
    ) THEN
        IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name   = 'analyses'
              AND column_name  = 'lead_id'
        ) THEN
            ALTER TABLE public.analyses RENAME COLUMN lead_id TO job_id;
        END IF;

        -- Ensure tech_stack is jsonb
        IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name   = 'analyses'
              AND column_name  = 'tech_stack'
              AND data_type    != 'jsonb'
        ) THEN
            ALTER TABLE public.analyses
                ALTER COLUMN tech_stack TYPE jsonb USING
                    CASE
                        WHEN tech_stack IS NULL THEN NULL
                        WHEN tech_stack ~ '^\\[' THEN tech_stack::jsonb
                        ELSE to_jsonb(tech_stack)
                    END;
        END IF;

        -- Ensure budget_min/max/spam_probability are float8
        IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name   = 'analyses'
              AND column_name  = 'budget_min'
              AND data_type    != 'double precision'
        ) THEN
            ALTER TABLE public.analyses
                ALTER COLUMN budget_min TYPE float8 USING budget_min::float8;
        END IF;

        IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name   = 'analyses'
              AND column_name  = 'budget_max'
              AND data_type    != 'double precision'
        ) THEN
            ALTER TABLE public.analyses
                ALTER COLUMN budget_max TYPE float8 USING budget_max::float8;
        END IF;

        IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name   = 'analyses'
              AND column_name  = 'spam_probability'
              AND data_type    != 'double precision'
        ) THEN
            ALTER TABLE public.analyses
                ALTER COLUMN spam_probability TYPE float8 USING spam_probability::float8;
        END IF;
    END IF;

END $$;
"""


class Migration(migrations.Migration):

    dependencies = [
        ("leads", "0005_seed_default_analysis"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=IDEMPOTENT_JOBS_SCHEMA,
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
            state_operations=[
                # Rename the model class from Lead to Job
                migrations.RenameModel(
                    old_name="Lead",
                    new_name="Job",
                ),
                # Change id to CharField (text PK)
                migrations.AlterField(
                    model_name="Job",
                    name="id",
                    field=models.CharField(primary_key=True, max_length=255, serialize=False),
                ),
                # Add description field
                migrations.AddField(
                    model_name="Job",
                    name="description",
                    field=models.TextField(null=True, blank=True),
                ),
                # Remove created_at
                migrations.RemoveField(
                    model_name="Job",
                    name="created_at",
                ),
                # Remove updated_at
                migrations.RemoveField(
                    model_name="Job",
                    name="updated_at",
                ),
                # Point Django at the new table name
                migrations.AlterModelTable(
                    name="Job",
                    table="jobs",
                ),
            ],
        ),
    ]
