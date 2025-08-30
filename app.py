import os
from datetime import datetime, timedelta
import random
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

app = Flask(__name__)

# Secrets & DB
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")
db_url = os.environ.get("DATABASE_URL", "sqlite:///wellatlas.db")
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

# ---------- Models ----------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    sites = db.relationship("Site", backref="customer", cascade="all, delete-orphan")

class Site(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey("customer.id"), nullable=False)
    jobs = db.relationship("Job", backref="site", cascade="all, delete-orphan")

class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_number = db.Column(db.String(50), nullable=False)
    category = db.Column(db.String(50), nullable=False)  # Domestic, Ag, Drilling, Electrical
    site_id = db.Column(db.Integer, db.ForeignKey("site.id"), nullable=False)
    entries = db.relationship("Entry", backref="job", cascade="all, delete-orphan")

class Entry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    job_id = db.Column(db.Integer, db.ForeignKey("job.id"), nullable=False)
    created_by = db.Column(db.String(150), nullable=True)
    attachment_name = db.Column(db.String(200), nullable=True)

@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except Exception:
        return None

# ---------- Safe init & seed ----------
_initialized = False

def ensure_db_and_seed():
    global _initialized
    if _initialized:
        return
    with app.app_context():
        db.create_all()
        # Seed only if empty
        if not Customer.query.first():
            seed_big_demo()
    _initialized = True

def seed_big_demo():
    # Town anchors (exact city centers)
    towns = [
        ("Corning", 39.9271, -122.1792),
        ("Orland", 39.7471, -122.1969),
        ("Chico", 39.7285, -121.8375),
        ("Cottonwood", 40.3863, -122.2803),
        ("Durham", 39.6468, -121.8005),
    ]
    # 20 presidents (first 20)
    presidents = [
        "Washington","Adams","Jefferson","Madison","Monroe",
        "Jackson","Van Buren","Harrison","Tyler","Polk",
        "Taylor","Fillmore","Pierce","Buchanan","Lincoln",
        "Johnson","Grant","Hayes","Garfield","Arthur"
    ]
    categories = ["Domestic","Ag","Drilling","Electrical"]
    today = datetime.utcnow()

    rnd = random.Random(1337)  # deterministic

    for p_idx, pres in enumerate(presidents):
        cust = Customer(name=pres)
        db.session.add(cust)
        db.session.flush()

        # 30 sites per customer
        for s_idx in range(30):
            town = towns[(p_idx + s_idx) % len(towns)]
            # Small jitter around the town center to avoid overlapping markers
            lat_jit = town[1] + (rnd.random()-0.5)*0.06
            lng_jit = town[2] + (rnd.random()-0.5)*0.06
            site = Site(
                name=f"{pres} Site {s_idx+1} ({town[0]})",
                latitude=lat_jit, longitude=lng_jit,
                customer_id=cust.id
            )
            db.session.add(site)
            db.session.flush()

            # 4 jobs per site (all categories)
            for cat in categories:
                job_num = f"{pres[:3].upper()}-{s_idx+1}-{cat[:3].upper()}"
                job = Job(job_number=job_num, category=cat, site_id=site.id)
                db.session.add(job)
                db.session.flush()

                # Category-specific entries over last days
                if cat == "Drilling":
                    entries = [
                        ("Rig mobilized", 9, "rig_mobilized.txt"),
                        ("As-built added", 6, "as_built.pdf"),
                        ("Well log updated", 2, "well_log_updated.txt"),
                    ]
                elif cat == "Ag":
                    entries = [
                        ("Flow test completed", 8, "flow_test.csv"),
                        ("Pump curve logged", 5, "pump_curve.pdf"),
                        ("Filter system check", 2, "filter_check.txt"),
                    ]
                elif cat == "Electrical":
                    entries = [
                        ("Panel check completed", 7, "panel_check.txt"),
                        ("Motor test performed", 4, "motor_test.csv"),
                        ("Electrical inspection", 1, "inspection_report.pdf"),
                    ]
                else:  # Domestic
                    entries = [
                        ("Installed domestic pump", 10, "install_notes.txt"),
                        ("Chlorination complete", 6, "chlorination.txt"),
                        ("Well test data uploaded", 3, "well_test.csv"),
                    ]

                for text, days_ago, attach in entries:
                    e = Entry(
                        text=text,
                        created_at=today - timedelta(days=days_ago),
                        job_id=job.id,
                        created_by="seed",
                        attachment_name=attach
                    )
                    db.session.add(e)
    db.session.commit()

# ---------- Hooks ----------
@app.before_request
def _on_request():
    ensure_db_and_seed()

# ---------- Routes ----------
@app.route("/")
def index():
    # pass minimal site info
    sites = Site.query.all()
    site_data = [
        {"id": s.id, "name": s.name, "lat": s.latitude, "lng": s.longitude, "customer": s.customer.name}
        for s in sites
    ]
    maptiler_key = os.environ.get("MAPTILER_KEY", "get_your_own_OpIi9ZULNHzrELrKf3Mn")
    return render_template("index.html", sites=site_data, maptiler_key=maptiler_key)

# Auth
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        u = User.query.filter_by(username=request.form.get("username")).first()
        if u and u.password == request.form.get("password"):
            login_user(u)
            return redirect(url_for("index"))
        flash("Invalid credentials", "error")
    return render_template("login.html")

@app.route("/signup", methods=["GET","POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if not username or not password:
            flash("Username and password required", "error")
            return redirect(url_for("signup"))
        if User.query.filter_by(username=username).first():
            flash("Username already taken", "error")
            return redirect(url_for("signup"))
        db.session.add(User(username=username, password=password))
        db.session.commit()
        flash("Account created. Please log in.", "info")
        return redirect(url_for("login"))
    return render_template("signup.html")

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("login"))

# Lists / details
@app.route("/customers")
def customers():
    custs = Customer.query.order_by(Customer.name.asc()).all()
    return render_template("customers.html", customers=custs)

@app.route("/sites/<int:site_id>")
def site_detail(site_id):
    site = db.session.get(Site, site_id)
    if not site:
        flash("Site not found", "error")
        return redirect(url_for("index"))
    jobs_by_cat = {}
    for j in site.jobs:
        jobs_by_cat.setdefault(j.category, []).append(j)
    return render_template("site.html", site=site, jobs_by_cat=jobs_by_cat)

@app.route("/jobs/<int:job_id>")
def job_detail(job_id):
    job = db.session.get(Job, job_id)
    if not job:
        flash("Job not found", "error")
        return redirect(url_for("index"))
    entries = Entry.query.filter_by(job_id=job.id).order_by(Entry.created_at.desc()).all()
    return render_template("job.html", job=job, site=job.site, entries=entries)

@app.route("/jobs/<int:job_id>/entries/new", methods=["POST"])
@login_required
def add_entry(job_id):
    job = db.session.get(Job, job_id)
    if not job:
        flash("Job not found", "error")
        return redirect(url_for("index"))
    text = (request.form.get("text") or "").strip()
    attach = (request.form.get("attachment_name") or "").strip() or None
    if not text:
        flash("Entry text is required", "error")
        return redirect(url_for("job_detail", job_id=job_id))
    e = Entry(text=text, job_id=job.id, created_by=current_user.username, attachment_name=attach)
    db.session.add(e)
    db.session.commit()
    flash("Entry added.", "info")
    return redirect(url_for("job_detail", job_id=job_id))

# Health
@app.get("/healthz")
def healthz():
    return {"ok": True, "schema": "ok"}, 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=True)
