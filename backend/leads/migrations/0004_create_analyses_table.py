from django.db import migrations


CREATE_ANALYSES_TABLE = """
CREATE TABLE IF NOT EXISTS public.analyses (
    lead_id text PRIMARY KEY,
    score int4 NOT NULL,
    score_reasoning text,
    tech_stack text,
    urgency text,
    budget_quality text,
    budget_estimate text,
    budget_min float4,
    budget_max float4,
    spam_probability float4,
    client_seriousness text,
    proposal_draft text,
    risk_summary text,
    estimated_effort text,
    analyzed_at text NOT NULL
);
"""


class Migration(migrations.Migration):
    dependencies = [
        ("leads", "0003_seed_default_leads"),
    ]

    operations = [
        migrations.RunSQL(CREATE_ANALYSES_TABLE, migrations.RunSQL.noop),
    ]
