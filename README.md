# AI Data Analyst Agent

- `ai-data-analyst-agent-offline.html` — standalone CSV-only prototype, works with no backend, open directly in a browser
- `backend/` — FastAPI service (SQL-only generation, validated, audited) that also serves the connected frontend at `/`
- `render.yaml` — one-file deploy config for Render.com

Opening `backend/static/index.html` directly won't work — it needs to be served by the backend (it calls relative API routes). Either run the backend locally and visit `http://localhost:8000`, or deploy it (below).

## Deploy to Render (free tier)

1. **Push this folder to a GitHub repo.** From inside this folder:
   ```bash
   git init
   git add .
   git commit -m "AI Data Analyst Agent"
   git branch -M main
   git remote add origin https://github.com/<your-username>/<repo-name>.git
   git push -u origin main
   ```
   (Create the empty repo on GitHub first, if you haven't — github.com → New repository.)

2. **Get an Anthropic API key** if you don't already have one, from console.anthropic.com → API Keys.

3. **On Render:** New → Blueprint → connect the GitHub repo you just pushed. Render reads `render.yaml` automatically and configures the service.

4. **Set the one secret Render can't infer:** in the Render dashboard, under the new service → Environment, set `ANTHROPIC_API_KEY` to your key. (Everything else is already defined in `render.yaml`.)

5. **Deploy.** Render builds and starts the service. When it's live, you'll get a URL like `https://ai-data-analyst-agent.onrender.com` — open it, and the connected frontend loads and auto-connects to its own backend.

Free tier note: Render's free web services spin down after inactivity and take ~30-60s to wake up on the next request — expect a slow first load if it's been idle.

## What ships vs. what doesn't

This deploys the **demo** database (the same small `orders` table used for local testing) — not a real production data source, and there's still no auth (see the architecture doc's Phase 3). Good for showing someone the working flow at a real URL; not yet the thing you'd point at a real company database with multiple users.
