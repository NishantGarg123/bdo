"""Django management command: refresh_jobs

Wraps the job_refresh module so it can be run inside the Docker container
via Django's management interface:

    python manage.py refresh_jobs <job_id> [<job_id> ...]

This command does NOT modify any existing Django app logic.
"""
