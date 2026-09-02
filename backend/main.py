"""
FastAPI backend for the AI Data Analyst Agent (Phase 1 of the
architecture doc): a backend service holds the database credential,
the model is constrained to write SQL, and every query is validated,
row-capped, executed in a rolled-back transaction, and logged before
the result goes back to the browser.

Run it:
    cp .env.example .env        # then fill in ANTHROPIC_API_KEY
    pip install -r requirements.txt
    python seed_demo_db.py      # creates a small demo SQLite db
    uvicorn main:app --reload

Then:
    curl http://localhost:8000/schema
    curl -X POST http://localhost:8000/ask \\
         -H "Content-Type: application/json" \\
         -d '{"question": "total revenue by region"}'

NOTE ON AUTH: this scaffold has no authentication layer yet. Section
4.5 of the architecture doc covers adding real auth + row-level
security -- do that before pointing this at a database with more than
one user's data, or with anything sensitive in it.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

import agent
import audit
import db
from models import AskRequest, AskResponse, SchemaResponse
from sql_guard import SqlValidationError, validate_and_prepare
from config import settings

app = FastAPI(title="AI Data Analyst Agent API")

# Tighten this to your actual frontend origin if you ever split the
# frontend out to a separate host. Same-origin deployment (the default
# here) doesn't need this at all, but it's left permissive for local
# dev flexibility.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).parent / "static"


@app.get("/")
def serve_frontend():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/schema", response_model=SchemaResponse)
def get_schema():
    """Live introspection of the connected (read-only) database."""
    return {"tables": db.get_schema_summary()}


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest):
    question = request.question.strip()
    if not question:
        raise HTTPException(400, "question must not be empty")

    schema = db.get_schema_summary()
    if not schema:
        raise HTTPException(500, "No tables found in the connected database.")

    try:
        agent_result = agent.generate_sql(question, schema, settings.max_rows_returned)
    except agent.AgentResponseError as e:
        audit.log_query(question=question, sql="", row_count=0, user=None, error=str(e))
        raise HTTPException(502, f"Agent failed to produce a usable response: {e}")

    raw_sql = agent_result["sql"]

    try:
        safe_sql = validate_and_prepare(raw_sql, settings.max_rows_returned)
    except SqlValidationError as e:
        audit.log_query(question=question, sql=raw_sql, row_count=0, user=None, error=str(e))
        # Deliberately 422, not 500: this is a rejected request, not a server fault.
        raise HTTPException(422, f"Generated SQL failed validation and was not run: {e}")

    try:
        rows = db.run_select(safe_sql)
    except Exception as e:
        audit.log_query(question=question, sql=safe_sql, row_count=0, user=None, error=str(e))
        raise HTTPException(500, f"Query execution failed: {e}")

    audit.log_query(question=question, sql=safe_sql, row_count=len(rows), user=None)

    return AskResponse(
        explanation=agent_result["explanation"],
        sql=safe_sql,
        chart_type=agent_result.get("chart_type", "none"),
        rows=rows,
        row_count=len(rows),
    )
