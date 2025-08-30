# WellAtlas 2.1 (Seeded) — with MapTiler Satellite + Google Drive Backup

This is a stable, demo-friendly build:
- **Customers → Sites → Jobs** hierarchy
- **Jobs** hold `category` (Domestic/Ag/Drilling/Electrical) and `status`
- Full **CRUD** for Customers, Sites, Jobs
- **Resets & reseeds** demo data on each deploy: 20 customers, each with 30 sites, each with 2 jobs
- **MapTiler Satellite** map on Site pages (fallback to OpenStreetMap if no key)
- **Google Drive backup** endpoint `/admin/backup`

## Quick Deploy (Render)
1. Create a **Web Service** on Render, connect this repo or upload these files.
2. **Build Command**: `pip install -r requirements.txt`
3. **Start Command**: `gunicorn app:app`
4. Add **Environment** (Settings → Environment):
   - `SECRET_KEY` = any random string
   - `MAPTILER_KEY` = (optional) your key from maptiler.com
   - `BACKUP_KEY` = (optional) secret token for /admin/backup (e.g. `mysecret`)
   - `GOOGLE_SERVICE_ACCOUNT_JSON` = (optional) paste the JSON from your Google Cloud service account **as one line**
     - Share a Drive folder with your service account email if you want uploads to land there
   - `GDRIVE_FOLDER_ID` = (optional) an existing Drive folder id. If omitted, a folder named **WellAtlas Backups** is created at first upload.
5. **runtime.txt** already pins Python to **3.12.5** (compatible with psycopg2).

## How to Use
- Go to **Customers** → pick a customer → create **Sites**
- On **New Site** and **Site Detail** pages you can set/adjust **Latitude/Longitude** on the map
- Inside a **Site**, add **Jobs** (with Category + Status)
- Filter Jobs by Category on the Site page

## MapTiler
- Get a key at https://www.maptiler.com/
- Set the environment variable `MAPTILER_KEY` to enable satellite tiles
- Without a key, the map automatically falls back to OpenStreetMap

## Google Drive Backup
- Create a **Service Account** in Google Cloud → enable **Drive API**
- Create a JSON key and copy its full contents into the `GOOGLE_SERVICE_ACCOUNT_JSON` env var (as a single line)
- (Optional) Share a Google Drive folder with the service account email (you'll see it in the JSON). Put that folder ID into `GDRIVE_FOLDER_ID`. If you skip this, the app creates a **WellAtlas Backups** folder in the service account drive.
- Trigger backup:
  - If you set `BACKUP_KEY=mysecret`: open `/admin/backup?key=mysecret`
  - If `BACKUP_KEY` is not set, `/admin/backup` is open (demo mode)

## Notes
- This demo uses SQLite by default (`wellatlas2_1.db`). To use Postgres, set `DATABASE_URL` (Render’s Postgres add-on will provide it automatically) — the app will use it if present.
- Because this is a **seeded demo**, data resets each deploy. Persistent storage will be added in later versions.
- Healthcheck: `/admin/healthz` returns `{ ok: true }`

Enjoy!
