# AI Data Analyst Agent — Backend (Phase 1 scaffold)

This is the Phase 1 backend from the architecture doc: a service that holds
the database credential, asks Claude for **SQL only**, validates that SQL
before running it, and logs every query. It replaces the browser-only
prototype's `new Function()` execution with something safe to point at a
real, shared database.

## What this does and doesn't include

**Included:**
- FastAPI service with `/schema` and `/ask` endpoints
- Live schema introspection (never hardcoded)
- SQL-only generation via Claude, validated with `sqlparse` before execution
  (single `SELECT` only, no DDL/DML, forced row limit)
- Queries run inside a transaction that's always rolled back
- Append-only audit log of every question, generated SQL, and row count

**Not included yet** (see architecture doc, sections 4.3–4.7, and the
rollout phase table):
- Authentication / row-level security — **do not** point this at a
  multi-tenant or sensitive database until Phase 3 is done
- Schema RAG for databases too large to fit in one prompt
- Sandboxed non-SQL code execution
- Production-grade audit storage (this scaffold just appends to a JSONL file)
- Rate limiting / cost controls beyond the row cap

## Setup

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env and set ANTHROPIC_API_KEY

python seed_demo_db.py     # creates demo.db with a small orders table
uvicorn main:app --reload
```

## Try it

```bash
curl http://localhost:8000/schema

curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "total revenue by region"}'
```

Response:
```json
{
  "explanation": "...",
  "sql": "SELECT region, SUM(revenue) AS total_revenue FROM orders GROUP BY region\nLIMIT 500",
  "chart_type": "bar",
  "rows": [{"region": "West", "total_revenue": 4250.5}, ...],
  "row_count": 4
}
```

## Pointing this at a real database

1. Create a **read-only** database role/user, scoped only to the
   schemas/tables you want the agent to see. Never use an admin or
   application-write credential here.
2. Set `DATABASE_URL` in `.env` to that role's connection string, e.g.
   `postgresql+psycopg2://readonly_user:pw@host:5432/dbname`
3. Install the matching SQLAlchemy driver (`psycopg2-binary` for Postgres,
   `pymysql` for MySQL, etc.) — not included in `requirements.txt` since it
   depends on your database.
4. `QUERY_TIMEOUT_SECONDS` in `.env` is read but not yet wired to a driver-level
   statement timeout — for Postgres, set it via `options="-c statement_timeout=Ns"`
   in the connection string, or `SET LOCAL statement_timeout` inside the
   transaction in `db.py`.

## Wiring up the frontend

There are now two frontends:
- `ai-data-analyst-agent.html` — the original CSV-only prototype, still useful offline, no backend needed
- `ai-data-analyst-agent-connected.html` — talks to this backend directly: enter the backend URL (default `http://localhost:8000`), hit Connect, and it fetches the live schema from `/schema` and sends questions to `/ask`

To use the connected version: start this backend (`uvicorn main:app --reload`), open `ai-data-analyst-agent-connected.html` in a browser, and connect to `http://localhost:8000`. CORS is wide open (`allow_origins=["*"]`) in this scaffold for local development — tighten it to your actual frontend's origin before deploying anywhere real.
