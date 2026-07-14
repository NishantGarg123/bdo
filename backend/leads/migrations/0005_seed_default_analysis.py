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


DEFAULT_ANALYSIS = {
    "lead_id": "10",
    "score": 85,
    "score_reasoning": (
        "This opportunity is attractive due to its clear responsibilities, full-time remote "
        "nature, and competitive hourly rate. The role offers a chance to work in a growing "
        "industry with a structured process, though it requires strong organizational skills "
        "and multitasking ability."
    ),
    "tech_stack": '["Trello", "Slack", "Airbnb platform"]',
    "urgency": "high",
    "budget_quality": "good",
    "budget_estimate": "$15-$25/hr",
    "budget_min": 15.0,
    "budget_max": 25.0,
    "spam_probability": 0.0,
    "client_seriousness": "high",
    "proposal_draft": (
        "Dear [Client's Name],\n"
        "• High reliance on effective communication with landlords and property managers."
    ),
    "risk_summary": None,
    "estimated_effort": "Full-time, ongoing: 5 days per week, 8 hours per day. Initial setup and "
    "learning curve may take 1-2 weeks.",
    "analyzed_at": "2026-06-18T14:19:59.301750+00:00",
}


def seed_default_analysis(apps, schema_editor):
    columns = list(DEFAULT_ANALYSIS)
    placeholders = ", ".join(["%s"] * len(columns))
    assignments = ", ".join(
        f"{column} = EXCLUDED.{column}" for column in columns if column != "lead_id"
    )

    with schema_editor.connection.cursor() as cursor:
        # Repairs databases where 0004 is recorded as applied but the table was
        # removed or was never created outside Django's migration process.
        cursor.execute(CREATE_ANALYSES_TABLE)
        cursor.execute(
            f"""
            INSERT INTO public.analyses ({", ".join(columns)})
            VALUES ({placeholders})
            ON CONFLICT (lead_id) DO UPDATE SET {assignments}
            """,
            [DEFAULT_ANALYSIS[column] for column in columns],
        )


class Migration(migrations.Migration):
    dependencies = [
        ("leads", "0004_create_analyses_table"),
    ]

    operations = [
        migrations.RunPython(seed_default_analysis, migrations.RunPython.noop),
    ]
