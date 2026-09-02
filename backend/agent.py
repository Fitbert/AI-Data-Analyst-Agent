"""
Talks to Claude to turn a plain-English question + schema into SQL.

This mirrors the prototype's buildPrompt()/askQuestion(), with one
deliberate change: the model is asked for SQL, not general-purpose code,
because SQL is what sql_guard.py can actually validate before it runs
(architecture doc, section 4.2).
"""
from __future__ import annotations

import json

import anthropic

from config import settings

_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)


class AgentResponseError(ValueError):
    pass


def build_prompt(question: str, schema: list[dict], max_rows: int) -> str:
    schema_text = "\n".join(
        f"- {t['table']}: " + ", ".join(f"{c['name']} ({c['type']})" for c in t["columns"])
        for t in schema
    )
    return f"""You are a data analyst agent with READ-ONLY access to a SQL database.

Schema:
{schema_text}

User question: "{question}"

Respond with ONLY a raw JSON object (no markdown fences, no commentary) with exactly these fields:
{{
  "explanation": "2-3 plain-English sentences answering the question, written as if you already ran the analysis",
  "sql": "a single SELECT statement (standard SQL) that answers the question, using only the tables/columns listed above. Include an explicit LIMIT of at most {max_rows}. Never use INSERT, UPDATE, DELETE, DDL, or multiple statements.",
  "chart_type": "bar" | "line" | "pie" | "none"
}}

If chart_type is not "none", the query's result columns should be interpretable as (label, value) pairs.
Only use tables and columns that appear in the schema above -- never invent one."""


def generate_sql(question: str, schema: list[dict], max_rows: int) -> dict:
    prompt = build_prompt(question, schema, max_rows)

    response = _client.messages.create(
        model=settings.anthropic_model,
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}],
    )

    text_block = next((b for b in response.content if b.type == "text"), None)
    if text_block is None:
        raise AgentResponseError("Model returned no text content.")

    cleaned = text_block.text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```", 2)[1]
        cleaned = cleaned[4:] if cleaned.lower().startswith("json") else cleaned
    cleaned = cleaned.strip().strip("`").strip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise AgentResponseError(f"Could not parse model response as JSON: {e}") from e

    for field in ("explanation", "sql", "chart_type"):
        if field not in parsed:
            raise AgentResponseError(f"Model response missing required field '{field}'.")

    return parsed
