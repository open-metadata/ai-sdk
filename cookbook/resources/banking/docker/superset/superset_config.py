"""Superset configuration for the banking local demo.

This file is mounted into the container at /app/pythonpath/superset_config.py
and is loaded automatically by Superset on startup.

Notes:
- This config is intentionally minimal and tuned for a local demo. Do not
  use it as-is in production (CSRF is disabled, the secret comes from env,
  etc.).
"""

import os

# Used to sign cookies. Generated/passed via docker-compose env.
SECRET_KEY = os.environ.get(
    "SUPERSET_SECRET_KEY", "thisISaSECRET_1234567890_changeMe"
)

# Superset's own metadata database (NOT the analytics warehouse). Defaults to
# the Postgres service defined in docker-compose.yml.
SQLALCHEMY_DATABASE_URI = os.environ.get(
    "SUPERSET_METADATA_DB_URI",
    "postgresql+psycopg2://superset:superset@superset-db:5432/superset",
)

# Feature flags enabled for the demo. Native filters + cross filters give a
# richer dashboarding experience; template processing lets users embed
# Jinja in SQL Lab.
FEATURE_FLAGS = {
    "DASHBOARD_NATIVE_FILTERS": True,
    "DASHBOARD_CROSS_FILTERS": True,
    "ENABLE_TEMPLATE_PROCESSING": True,
}

# Cap how many rows can be returned to a chart. 50k is more than enough for
# the cookbook marts but small enough to keep the UI responsive.
ROW_LIMIT = 50000

# Demo-only: disable CSRF so the provisioning script can POST without
# negotiating a token round-trip through a browser. Re-enable for any
# real-world deployment.
WTF_CSRF_ENABLED = False
