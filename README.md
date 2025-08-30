# WellAtlas 2.3 (MapTiler fix)

This version loads MapTiler **satellite** tiles using an environment variable.

## Deploy (Render)
1. Create a new **Web Service** from this repo.
2. Build Command: `pip install -r requirements.txt`
3. Start Command: `web: gunicorn app:app`
4. Add an Environment Variable:
   - Key: `MAPTILER_KEY`
   - Value: (your key from https://cloud.maptiler.com/account/keys/)
5. Deploy. Open `/` to see the satellite map with pins.
