"""
job_refresh.config
~~~~~~~~~~~~~~~~~~
Loads configuration from environment variables.
All callers import from here so credential handling stays in one place.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env files from both backend/ and the project root, giving the root
# file priority (same order as Django settings.py).
_BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(_BACKEND_DIR / ".env")
load_dotenv(_BACKEND_DIR.parent / ".env")


# ── Upwork API ──────────────────────────────────────────────────────────────

UPWORK_ACCESS_TOKEN: str = os.getenv("UPWORK_ACCESS_TOKEN", "")
GRAPHQL_ENDPOINT: str = os.getenv(
    "UPWORK_GRAPHQL_ENDPOINT",
    "https://api.upwork.com/graphql",
)

# ── PostgreSQL ──────────────────────────────────────────────────────────────

DB_CONFIG: dict[str, str | int] = {
    "dbname": os.getenv("DB_NAME", "bdo_leads"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "postgres"),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
}
