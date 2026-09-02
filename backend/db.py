"""
Database access layer.

Design intent (see architecture doc, section 4.1-4.2):
- The engine should be created from a connection string that points at a
  READ-ONLY database role/user. This module does not enforce that at
  connection time -- it must be enforced by how the role is provisioned
  in the database itself. Application-level checks (sql_guard.py) are a
  second layer of defense, not a substitute for least-privilege access.
- Every query runs inside a transaction that is always rolled back, so
  even if a write somehow got past validation, it cannot persist.
- A row-count ceiling is enforced here in Python as a backstop, in
  addition to the LIMIT injected by sql_guard.py.
"""
from __future__ import annotations

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine

from config import settings

_engine: Engine | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_engine(settings.database_url, pool_pre_ping=True)
    return _engine


def get_schema_summary() -> list[dict]:
    """
    Introspect the live database and return a compact schema description
    suitable for prompting the model. This is intentionally re-fetched
    (not hardcoded) so it can never drift from what actually exists.

    For a database with many tables, replace this with a retrieval step
    (see architecture doc, section 4.3) that returns only tables relevant
    to the current question instead of the whole schema.
    """
    engine = get_engine()
    inspector = inspect(engine)
    tables = []
    for table_name in inspector.get_table_names():
        columns = [
            {"name": col["name"], "type": str(col["type"])}
            for col in inspector.get_columns(table_name)
        ]
        tables.append({"table": table_name, "columns": columns})
    return tables


def run_select(sql: str) -> list[dict]:
    """
    Execute a pre-validated, single SELECT statement and return rows as
    dicts. Always runs inside a transaction that gets rolled back, and
    always truncates to settings.max_rows_returned regardless of any
    LIMIT already in the SQL.
    """
    engine = get_engine()
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            result = conn.execute(text(sql))
            columns = list(result.keys())
            rows = []
            for i, row in enumerate(result):
                if i >= settings.max_rows_returned:
                    break
                rows.append(dict(zip(columns, row)))
            return rows
        finally:
            # Always roll back. This connection should never be able to
            # commit a write, even if validation upstream had a bug.
            trans.rollback()
