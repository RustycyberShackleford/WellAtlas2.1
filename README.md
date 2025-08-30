# WellAtlas 2.2

## Features
- Login/logout
- Customers, Sites, Jobs, Timeline entries
- Seeding of demo data (5 presidents × 5 sites × jobs × entries)
- Map with Leaflet

## Deploy on Render
1. Upload this repo.
2. Set **Start Command**: `gunicorn app:app`
3. Environment variables:
   - DATABASE_URL (Render gives you if you use PostgreSQL, else SQLite fallback)
   - SECRET_KEY (any random string)
