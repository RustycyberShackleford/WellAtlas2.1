# WellAtlas 2.0 — Satellite (MapTiler DEMO) • No Login
**What you get**
- Homepage = **satellite map** (MapTiler demo key baked in) + Streets toggle
- Hierarchy: **Customer → Site → Job**
- Click a **pin** → popup shows **jobs** for that site (links to job pages)
- **Seeded demo data** across Corning / Orland / Chico / Cottonwood / Durham
- SQLite file `wellatlas.db` is created on first boot
- Health check: `/healthz`

## Deploy on Render (free)
1) Create a new GitHub repo and upload the **contents** of this zip (not the zip file).
2) Create a **Web Service** on Render and connect the repo.
3) Render auto-detects:
   - `Procfile`: `web: gunicorn app:app`
   - `runtime.txt`: `python-3.12.6`
4) Click **Deploy**. First boot creates and seeds the database.
5) Visit `/` for the map, `/customers` to browse.

### Optional env var
- `SECRET_KEY` — any random string (used by Flask for session signing). Not required for this no-auth build.

## Local run
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
# open http://127.0.0.1:5000
```

## MapTiler key
This build uses the **demo key** inline. For production later, make a free account and
replace the key in `templates/index.html` with your own.
