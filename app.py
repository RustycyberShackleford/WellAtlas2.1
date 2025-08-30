import os, io, json
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, jsonify, abort
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker
from models import Base, Customer, Site, Job

# Google Drive
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY","wellatlas-2-1-dev")
app.config["PROPAGATE_EXCEPTIONS"] = True

DATABASE_URL = os.environ.get("DATABASE_URL","").replace("postgres://","postgresql://")
if not DATABASE_URL:
    # default to SQLite for quick start
    DATABASE_URL = "sqlite:///wellatlas2_1.db"

engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

MAPTILER_KEY = os.environ.get("MAPTILER_KEY","")
BACKUP_KEY = os.environ.get("BACKUP_KEY","")  # optional shared secret for /admin/backup
GDRIVE_JSON = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON") or os.environ.get("GOOGLE_DRIVE_CREDENTIALS")
GDRIVE_FOLDER_ID = os.environ.get("GDRIVE_FOLDER_ID","")
GDRIVE_FOLDER_NAME = os.environ.get("GDRIVE_FOLDER_NAME","WellAtlas Backups")

# --- RESET & SEED on each boot ---
def reset_and_seed():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    s = SessionLocal()
    try:
        categories = ["Domestic","Ag","Drilling","Electrical"]
        # 20 customers, 30 sites each, 2 jobs each
        for c_idx in range(1, 21):
            cust = Customer(name=f"Customer {c_idx}")
            s.add(cust); s.flush()
            for s_idx in range(1, 31):
                # deterministic lat/lng scatter (roughly CA area) for demo
                lat = 32.5 + (s_idx % 15) * 0.5
                lng = -124.0 + (s_idx % 15) * 0.6
                site = Site(name=f"Site {s_idx} (Cust {c_idx})", customer_id=cust.id,
                            latitude=lat, longitude=lng)
                s.add(site); s.flush()
                j1 = Job(job_number=f"{c_idx}-{s_idx:02d}-01", category=categories[(s_idx) % 4], status="Active", site_id=site.id)
                j2 = Job(job_number=f"{c_idx}-{s_idx:02d}-02", category=categories[(s_idx+1) % 4], status="Completed", site_id=site.id)
                s.add_all([j1, j2])
        s.commit()
    finally:
        s.close()

reset_and_seed()

@app.get("/admin/healthz")
def healthz():
    return jsonify(ok=True)

@app.get("/")
def index():
    s = SessionLocal()
    try:
        cust_count = s.scalar(select(func.count(Customer.id)))
        site_count = s.scalar(select(func.count(Site.id)))
        job_count  = s.scalar(select(func.count(Job.id)))
    finally:
        s.close()
    return render_template("index.html", counts={"customers":cust_count, "sites":site_count, "jobs":job_count})

# --- Customers ---
@app.get("/customers")
def customers():
    s = SessionLocal()
    try:
        rows = s.execute(select(Customer)).scalars().all()
        site_counts = {cid:cnt for cid,cnt in s.execute(select(Site.customer_id, func.count()).group_by(Site.customer_id)).all()}
        for c in rows:
            c.site_count = site_counts.get(c.id, 0)
    finally:
        s.close()
    return render_template("customers.html", customers=rows)

# alias if older templates refer to list_customers
app.add_url_rule("/customers", endpoint="list_customers", view_func=customers)

@app.route("/customers/new", methods=["GET","POST"])
def new_customer():
    if request.method == "POST":
        name = request.form.get("name","").strip()
        if name:
            s = SessionLocal()
            try:
                s.add(Customer(name=name)); s.commit()
            finally:
                s.close()
            return redirect(url_for("customers"))
    return render_template("new_customer.html")

@app.route("/customers/<int:customer_id>")
def customer_detail(customer_id):
    s = SessionLocal()
    try:
        c = s.get(Customer, customer_id)
        if not c: return redirect(url_for("customers"))
        sites = s.execute(select(Site).where(Site.customer_id==customer_id)).scalars().all()
        job_counts = {sid:cnt for sid,cnt in s.execute(select(Job.site_id, func.count()).group_by(Job.site_id)).all()}
        for site in sites:
            site.job_count = job_counts.get(site.id, 0)
    finally:
        s.close()
    return render_template("customer_detail.html", customer=c, sites=sites)

@app.route("/customers/<int:customer_id>/edit", methods=["GET","POST"])
def edit_customer(customer_id):
    s = SessionLocal()
    try:
        c = s.get(Customer, customer_id)
        if not c: return redirect(url_for("customers"))
        if request.method == "POST":
            c.name = request.form.get("name","").strip() or c.name
            s.commit()
            return redirect(url_for("customers"))
    finally:
        s.close()
    return render_template("edit_customer.html", customer=c)

@app.route("/customers/<int:customer_id>/delete")
def delete_customer(customer_id):
    s = SessionLocal()
    try:
        c = s.get(Customer, customer_id)
        if c:
            s.delete(c); s.commit()
    finally:
        s.close()
    return redirect(url_for("customers"))

# --- Sites ---
@app.route("/customers/<int:customer_id>/sites/new", methods=["GET","POST"])
def new_site(customer_id):
    s = SessionLocal()
    try:
        c = s.get(Customer, customer_id)
        if not c: return redirect(url_for("customers"))
        if request.method == "POST":
            name = request.form.get("name","").strip()
            lat = request.form.get("latitude","").strip()
            lng = request.form.get("longitude","").strip()
            lat_v = float(lat) if lat else None
            lng_v = float(lng) if lng else None
            if name:
                s.add(Site(name=name, customer_id=customer_id, latitude=lat_v, longitude=lng_v)); s.commit()
                return redirect(url_for("customer_detail", customer_id=customer_id))
    finally:
        s.close()
    return render_template("new_site.html", customer=c, maptile_key=MAPTILER_KEY)

@app.route("/sites/<int:site_id>")
def site_detail(site_id):
    s = SessionLocal()
    try:
        site = s.get(Site, site_id)
        if not site: return redirect(url_for("customers"))
        cat = request.args.get("category","").strip()
        q = select(Job).where(Job.site_id==site_id)
        selected_category = ""
        if cat:
            q = q.where(Job.category==cat)
            selected_category = cat
        jobs = s.execute(q.order_by(Job.updated_at.desc())).scalars().all()
    finally:
        s.close()
    return render_template("site_detail.html", site=site, jobs=jobs, selected_category=selected_category, maptile_key=MAPTILER_KEY)

@app.route("/sites/<int:site_id>/edit", methods=["GET","POST"])
def edit_site(site_id):
    s = SessionLocal()
    try:
        site = s.get(Site, site_id)
        if not site: return redirect(url_for("customers"))
        if request.method == "POST":
            site.name = request.form.get("name","").strip() or site.name
            lat = request.form.get("latitude","").strip()
            lng = request.form.get("longitude","").strip()
            site.latitude = float(lat) if lat else None
            site.longitude = float(lng) if lng else None
            s.commit()
            return redirect(url_for("customer_detail", customer_id=site.customer_id))
    finally:
        s.close()
    return render_template("edit_site.html", site=site)

@app.route("/sites/<int:site_id>/coords", methods=["POST"])
def save_site_coords(site_id):
    s = SessionLocal()
    try:
        site = s.get(Site, site_id)
        if not site: abort(404)
        lat = request.form.get("latitude","").strip()
        lng = request.form.get("longitude","").strip()
        site.latitude = float(lat) if lat else None
        site.longitude = float(lng) if lng else None
        s.commit()
        return redirect(url_for("site_detail", site_id=site_id))
    finally:
        s.close()

# --- Jobs ---
@app.route("/jobs/new/<int:site_id>", methods=["GET","POST"])
def new_job(site_id):
    s = SessionLocal()
    try:
        site = s.get(Site, site_id)
        if not site: return redirect(url_for("customers"))
        if request.method == "POST":
            job_number = request.form.get("job_number","").strip()
            category = request.form.get("category","").strip()
            status = request.form.get("status","").strip()
            if job_number and category and status:
                s.add(Job(job_number=job_number, category=category, status=status, site_id=site_id))
                s.commit()
                return redirect(url_for("site_detail", site_id=site_id))
    finally:
        s.close()
    return render_template("new_job.html", site=site)

@app.route("/jobs/<int:job_id>")
def job_detail(job_id):
    s = SessionLocal()
    try:
        job = s.get(Job, job_id)
        if not job: return redirect(url_for("customers"))
        site = s.get(Site, job.site_id)
    finally:
        s.close()
    return render_template("job_detail.html", job=job, site=site)

@app.route("/jobs/<int:job_id>/edit", methods=["GET","POST"])
def edit_job(job_id):
    s = SessionLocal()
    try:
        job = s.get(Job, job_id)
        if not job: return redirect(url_for("customers"))
        if request.method == "POST":
            job.job_number = request.form.get("job_number","").strip() or job.job_number
            job.category = request.form.get("category","").strip() or job.category
            job.status = request.form.get("status","").strip() or job.status
            job.updated_at = datetime.utcnow()
            s.commit()
            return redirect(url_for("job_detail", job_id=job.id))
    finally:
        s.close()
    return render_template("edit_job.html", job=job)

@app.route("/jobs/<int:job_id>/delete")
def delete_job(job_id):
    s = SessionLocal()
    try:
        job = s.get(Job, job_id)
        if job:
            site_id = job.site_id
            s.delete(job); s.commit()
            return redirect(url_for("site_detail", site_id=site_id))
    finally:
        s.close()
    return redirect(url_for("customers"))

# --- Google Drive Backup ---
def _drive_service_or_none():
    if not GDRIVE_JSON:
        return None
    try:
        info = json.loads(GDRIVE_JSON)
        creds = Credentials.from_service_account_info(info, scopes=["https://www.googleapis.com/auth/drive.file"])
        return build("drive", "v3", credentials=creds, cache_discovery=False)
    except Exception as e:
        print("Drive init failed:", e)
        return None

def _ensure_folder(drive, folder_id, folder_name):
    if folder_id:
        return folder_id
    # search by name
    q = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    res = drive.files().list(q=q, spaces="drive", fields="files(id,name)", pageSize=10).execute()
    items = res.get("files", [])
    if items:
        return items[0]["id"]
    # create folder
    meta = {"name": folder_name, "mimeType": "application/vnd.google-apps.folder"}
    newf = drive.files().create(body=meta, fields="id").execute()
    return newf["id"]

def _export_json_bytes():
    s = SessionLocal()
    try:
        data = {"customers":[], "sites":[], "jobs":[]}
        for c in s.execute(select(Customer)).scalars().all():
            data["customers"].append({"id":c.id, "name":c.name})
        for si in s.execute(select(Site)).scalars().all():
            data["sites"].append({"id":si.id, "name":si.name, "customer_id":si.customer_id,
                                  "latitude":si.latitude, "longitude":si.longitude})
        for j in s.execute(select(Job)).scalars().all():
            data["jobs"].append({"id":j.id, "job_number":j.job_number, "category":j.category,
                                 "status":j.status, "site_id":j.site_id,
                                 "created_at": (j.created_at.isoformat() if j.created_at else None),
                                 "updated_at": (j.updated_at.isoformat() if j.updated_at else None)})
        return json.dumps(data, indent=2).encode("utf-8")
    finally:
        s.close()

@app.route("/admin/backup")
def trigger_backup():
    if BACKUP_KEY and request.args.get("key") != BACKUP_KEY:
        return abort(403)
    payload = _export_json_bytes()
    drive = _drive_service_or_none()
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"wellatlas_backup_{stamp}.json"
    msg = "Backup created. "
    if drive:
        folder_id = _ensure_folder(drive, GDRIVE_FOLDER_ID, GDRIVE_FOLDER_NAME)
        media = MediaInMemoryUpload(payload, mimetype="application/json", resumable=False)
        meta = {"name": filename, "parents":[folder_id]}
        drive.files().create(body=meta, media_body=media, fields="id").execute()
        msg += "Uploaded to Google Drive."
    else:
        msg += "Set GOOGLE_SERVICE_ACCOUNT_JSON to upload to Drive."
    return msg, 200, {"Content-Type":"text/plain; charset=utf-8"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT","10000")), debug=True)
