"""Pytest bootstrap: keep the app off Postgres before config is imported.

The API tests override the ``get_db`` dependency with in-memory SQLite, so this
only prevents module import from resolving the default Postgres DSN.
"""

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SEED_ON_EMPTY", "false")
