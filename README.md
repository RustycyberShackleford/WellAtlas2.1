# WellAtlas 2.2 (Fallback Safe, MapTiler demo, Big Seed)

**What you get immediately after deploy (no env vars required):**
- Homepage = interactive map with site pins (MapTiler Satellite demo key baked in, falls back to OSM if needed)
- Login/Signup (no pre-seeded users; just sign up)
- Seeded demo data **once when DB is empty**:
  - **20 customers** (U.S. presidents)
  - **30 sites per customer** (≈600 total), spread across **Corning, Orland, Chico, Cottonwood, Durham**
  - **4 jobs per site**: Domestic, Ag, Drilling, Electrical
  - **Multiple timeline entries per job** across recent days
- CRUD for customers → sites → jobs → timeline entries

## Deploy on Render
1. Create a **new GitHub repo**, upload the **contents of this zip** (not the zip itself).
2. Create a new **Render → Web Service** from that repo.
3. It will auto-detect the `Procfile` and Python from `runtime.txt`.
4. Click **Deploy**. First boot creates `wellatlas.db` (SQLite) and seeds demo data.

### Optional later (persistence)
- Add **Render Postgres** and set **Environment Variable** `DATABASE_URL` (Render gives you a URL).
- The app will auto-switch to Postgres (and fixes `postgres://` → `postgresql://`).

### Optional MapTiler key
- Set env var **MAPTILER_KEY** to your own key. Otherwise a demo key is used.
- To get a key: https://cloud.maptiler.com/ (free tier).

### Local Dev
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
# open http://127.0.0.1:5000
```

**Default users:** none. Use **Sign up** to create the first account.
