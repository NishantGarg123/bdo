"""No-op migration placeholder.

The interviewing / invite_sent / hired tracking data lives in the externally
managed public.analyses table (not in jobs). No Django model fields or
database operations are needed here.
"""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("leads", "0002_add_analyzed_status"),
    ]

    operations = []
