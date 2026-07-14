from django.db import migrations


ALIGN_LEGACY_LEADS_TABLE = """
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'leads_lead' AND column_name = 'job_title'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'leads_lead' AND column_name = 'title'
    ) THEN
        ALTER TABLE leads_lead RENAME COLUMN job_title TO title;
    END IF;
END $$;

ALTER TABLE leads_lead ALTER COLUMN title TYPE varchar(500);
ALTER TABLE leads_lead ADD COLUMN IF NOT EXISTS url varchar(1000) NOT NULL DEFAULT '';
ALTER TABLE leads_lead ADD COLUMN IF NOT EXISTS budget varchar(100) NOT NULL DEFAULT '';
ALTER TABLE leads_lead ADD COLUMN IF NOT EXISTS budget_min double precision;
ALTER TABLE leads_lead ADD COLUMN IF NOT EXISTS budget_max double precision;
ALTER TABLE leads_lead ADD COLUMN IF NOT EXISTS skills jsonb NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE leads_lead ADD COLUMN IF NOT EXISTS job_type varchar(100) NOT NULL DEFAULT '';
ALTER TABLE leads_lead ADD COLUMN IF NOT EXISTS posted_at timestamp with time zone;
ALTER TABLE leads_lead ADD COLUMN IF NOT EXISTS fetched_at timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE leads_lead ADD COLUMN IF NOT EXISTS skip_reason varchar(500) NOT NULL DEFAULT '';
ALTER TABLE leads_lead ADD COLUMN IF NOT EXISTS total_proposals integer NOT NULL DEFAULT 0;

UPDATE leads_lead
SET status = CASE status
    WHEN 'new' THEN 'pending'
    WHEN 'interview' THEN 'in_progress'
    ELSE status
END;

ALTER TABLE leads_lead DROP COLUMN IF EXISTS company_name;
ALTER TABLE leads_lead DROP COLUMN IF EXISTS location;
ALTER TABLE leads_lead DROP COLUMN IF EXISTS notes;
ALTER TABLE leads_lead DROP COLUMN IF EXISTS created_by_id;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("leads", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[migrations.RunSQL(ALIGN_LEGACY_LEADS_TABLE)],
            state_operations=[],
        ),
    ]
