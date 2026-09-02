"""
Validates model-generated SQL before it ever reaches the database.

This is the single highest-leverage safety layer in the whole system
(architecture doc, section 4.2). It does NOT try to be a general SQL
firewall -- it enforces a narrow allowlist: exactly one read-only SELECT
statement, nothing else.
"""
from __future__ import annotations

import re

import sqlparse
from sqlparse.sql import Statement
from sqlparse.tokens import DDL, DML

FORBIDDEN_KEYWORDS = {
    "insert", "update", "delete", "drop", "alter", "create", "truncate",
    "grant", "revoke", "attach", "pragma", "vacuum", "replace", "merge",
    "exec", "execute", "call",
}


class SqlValidationError(ValueError):
    pass


def validate_and_prepare(raw_sql: str, max_rows: int) -> str:
    """
    Raises SqlValidationError if the SQL is not a single, safe SELECT.
    Returns the SQL with a LIMIT clause guaranteed to be present and
    no larger than max_rows.
    """
    sql = raw_sql.strip().rstrip(";")

    if not sql:
        raise SqlValidationError("Generated SQL was empty.")

    statements = sqlparse.parse(sql)
    if len(statements) != 1:
        raise SqlValidationError(
            f"Expected exactly one SQL statement, got {len(statements)}."
        )

    statement: Statement = statements[0]
    _assert_single_select(statement)
    _assert_no_forbidden_keywords(sql)

    return _ensure_limit(sql, max_rows)


def _assert_single_select(statement: Statement) -> None:
    stmt_type = statement.get_type()
    if stmt_type != "SELECT":
        raise SqlValidationError(
            f"Only SELECT statements are allowed; model produced '{stmt_type}'."
        )

    # Guard against a DML/DDL token hiding inside a SELECT via a
    # subquery, CTE trick, or statement the parser mis-typed.
    for token in statement.flatten():
        if token.ttype in (DDL, DML) and token.value.lower() != "select":
            raise SqlValidationError(
                f"Disallowed keyword found in query: '{token.value}'."
            )


def _assert_no_forbidden_keywords(sql: str) -> None:
    lowered = sql.lower()
    for word in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{re.escape(word)}\b", lowered):
            raise SqlValidationError(f"Disallowed keyword found in query: '{word}'.")


def _ensure_limit(sql: str, max_rows: int) -> str:
    """
    If the query already has a LIMIT, cap it at max_rows. Otherwise
    append one. This is a backstop -- db.run_select() also truncates
    in Python regardless of what LIMIT ends up in the SQL.
    """
    match = re.search(r"\blimit\s+(\d+)\b", sql, flags=re.IGNORECASE)
    if match:
        existing_limit = int(match.group(1))
        if existing_limit > max_rows:
            sql = sql[: match.start(1)] + str(max_rows) + sql[match.end(1):]
        return sql
    return f"{sql}\nLIMIT {max_rows}"
