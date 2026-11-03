
import sqlite3
from contextlib import contextmanager

from app.config import DATABASE_PATH


def init_db():
    """
    Validate the existing assessment database.
    Do not create or modify its tables.
    """
    if not DATABASE_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DATABASE_PATH}"
        )

    required_tables = {
        "employees",
        "leave_balances",
        "leave_requests",
        "public_holidays",
    }

    with sqlite3.connect(str(DATABASE_PATH)) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }

        missing = required_tables - tables

        if missing:
            raise RuntimeError(
                f"Missing required assessment tables: {sorted(missing)}"
            )


@contextmanager
def get_connection():
    """Open a database connection with transaction management."""

    connection = sqlite3.connect(
        str(DATABASE_PATH),
        timeout=30
    )

    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    try:
        yield connection
        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()
