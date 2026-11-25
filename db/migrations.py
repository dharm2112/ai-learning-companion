"""Create all database tables.

Safe to run multiple times — SQLAlchemy's create_all() is a no-op for
tables that already exist. Never drops or truncates data.

Run directly for a first-time setup:
    python db/migrations.py
"""

from __future__ import annotations

from db.database import Base, engine
# Import models so SQLAlchemy registers them against Base before create_all().
import db.models  # noqa: F401


def run_migrations() -> None:
    """Create all tables that do not yet exist."""
    Base.metadata.create_all(bind=engine)
    print("Database migrations complete.")


if __name__ == "__main__":
    run_migrations()
