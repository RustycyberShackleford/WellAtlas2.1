# WellAtlas 2.3 — Map + Customers → Sites → Jobs + Timeline (No Auth)

This build includes:
- Homepage map with **interactive pins** (Customer + Site; buttons to view Site or Jobs).
- **Customer → Site → Job** hierarchy pages.
- **Seed data** on empty DB: 5 customers (Presidents), 10 sites each, 4 jobs per site, multi‑day timeline entries.
- **"Find Sites Near Me"** button (lists closest sites without dropping new pins).
- Delete options for customers/sites/jobs (cascade).
- **No login/auth** yet. **No Google Drive** yet.

## Environment variables (Render → Environment)
- `MAPTILER_KEY` (required for satellite tiles). If missing, map falls back to OpenStreetMap.
- `FLASK_SECRET_KEY` (optional; defaults to dev-secret).
- `DATABASE_URL` (optional). If missing, uses local SQLite file `wellatlas.db`.

## Deploy on Render
1. Create a new **Web Service** from this repo.
2. Build command: `pip install -r requirements.txt`
3. Start command (from `Procfile`): `web: gunicorn app:app`
4. Add env var: `MAPTILER_KEY=your_real_key` (https://cloud.maptiler.com/account/keys/)
5. Manual Deploy → **Clear build cache & Deploy**.

Health check endpoint: `/healthz`

## Local run
```
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
# open http://127.0.0.1:5000
```
