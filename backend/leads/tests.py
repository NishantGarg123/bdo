from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import SimpleTestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITransactionTestCase

from .models import Job, LeadStatus


class UpworkActivityMappingTests(SimpleTestCase):
    """Guard the ID conversion and response-field mapping used by refresh."""

    def test_fetch_uses_plain_upwork_id_and_returns_database_id(self):
        from job_refresh import upwork_client

        payload = {
            "data": {
                "marketplaceJobPosting": {
                    "id": "~022084178164356493946",
                    "content": {"title": "Example job"},
                    "totalApplicants": 7,
                    "activityStat": {
                        "jobActivity": {
                            "invitesSent": 2,
                            "totalInvitedToInterview": 1,
                            "totalHired": 1,
                        }
                    },
                }
            }
        }

        with patch.object(upwork_client, "_execute", return_value=payload) as execute:
            result = upwork_client.fetch_job_activity("2084178164356493946")

        self.assertIsNotNone(result)
        self.assertEqual(execute.call_args.args[1], {"jobId": "2084178164356493946"})
        self.assertEqual(result.job_id, "2084178164356493946")
        self.assertEqual(result.total_applicants, 7)
        self.assertEqual(result.invites_sent, 2)
        self.assertTrue(result.interviewing)
        self.assertTrue(result.hired)


class LeadFilteringAndApplyTests(APITransactionTestCase):
    # ``jobs`` is externally provisioned in production, so its state-only
    # migration does not create it in Django's temporary test database.
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(Job)

    @classmethod
    def tearDownClass(cls):
        with connection.schema_editor() as schema_editor:
            schema_editor.delete_model(Job)
        super().tearDownClass()

    def setUp(self):
        self.user = get_user_model().objects.create_user("lead-tester", password="test-password")
        self.client.force_authenticate(self.user)
        now = timezone.now()
        self.recent_analyzed = Job.objects.create(
            id="recent-analyzed", title="Recent analyzed", status=LeadStatus.ANALYZED, fetched_at=now - timedelta(hours=12)
        )
        self.three_day_applied = Job.objects.create(
            id="three-day-applied", title="Three day applied", status=LeadStatus.APPLIED, fetched_at=now - timedelta(days=2)
        )
        Job.objects.create(
            id="old-pending", title="Old pending", status=LeadStatus.PENDING, fetched_at=now - timedelta(days=5)
        )

    def test_time_filter_changes_results_total_and_status_counts(self):
        last_day = self.client.get(reverse("lead-list"), {"time_filter": "24h"})
        three_days = self.client.get(reverse("lead-list"), {"time_filter": "3d"})

        self.assertEqual(last_day.status_code, 200)
        self.assertEqual(last_day.data["total"], 1)
        self.assertEqual(last_day.data["status_counts"][LeadStatus.ANALYZED], 1)
        self.assertEqual(last_day.data["status_counts"][LeadStatus.APPLIED], 0)

        self.assertEqual(three_days.status_code, 200)
        self.assertEqual(three_days.data["total"], 2)
        self.assertEqual(three_days.data["status_counts"][LeadStatus.ANALYZED], 1)
        self.assertEqual(three_days.data["status_counts"][LeadStatus.PENDING], 0)
        self.assertEqual(three_days.data["status_counts"][LeadStatus.APPLIED], 1)

    def test_applied_leads_endpoint_returns_only_applied_jobs(self):
        response = self.client.get(reverse("applied-lead-list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["total"], 1)
        self.assertEqual(response.data["results"][0]["id"], self.three_day_applied.id)
        self.assertEqual(response.data["results"][0]["status"], LeadStatus.APPLIED)

    def test_apply_persists_status_and_moves_lead_between_filters(self):
        response = self.client.post(reverse("lead-apply", kwargs={"pk": self.recent_analyzed.id}))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], LeadStatus.APPLIED)
        self.recent_analyzed.refresh_from_db()
        self.assertEqual(self.recent_analyzed.status, LeadStatus.APPLIED)

        analyzed = self.client.get(reverse("lead-list"), {"status": LeadStatus.ANALYZED, "time_filter": "24h"})
        applied = self.client.get(reverse("lead-list"), {"status": LeadStatus.APPLIED, "time_filter": "24h"})
        self.assertEqual(analyzed.data["total"], 0)
        self.assertEqual(applied.data["total"], 1)
        self.assertEqual(applied.data["status_counts"][LeadStatus.ANALYZED], 0)
        self.assertEqual(applied.data["status_counts"][LeadStatus.APPLIED], 1)
