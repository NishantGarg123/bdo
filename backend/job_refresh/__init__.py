"""
job_refresh — Upwork job refresh module.

Fetches the latest proposal / interviewing / invite_sent / hired data for
one or more Upwork job IDs and writes the values to the public.analyses table.

Usage
-----
As a standalone script (outside Docker):

    python -m job_refresh.refresh_jobs <job_id_1> <job_id_2> ...

As a library (e.g. inside a Django management command):

    from job_refresh import refresh_jobs
    results = refresh_jobs(["job_id_1", "job_id_2"])

Environment variables (inherit from backend/.env or root .env):

    UPWORK_ACCESS_TOKEN   – OAuth2 bearer token for the Upwork GraphQL API
    DB_NAME / DB_USER / DB_PASSWORD / DB_HOST / DB_PORT – PostgreSQL credentials
"""
