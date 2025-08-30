\
import os
from flask import Flask, render_template, redirect, url_for, flash
from models import db, Customer, Site, Job

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret")
db_url = os.environ.get("DATABASE_URL", "sqlite:///wellatlas.db")
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

_bootstrapped = False

def seed_demo():
    # 5 customers, 5 sites each, 4 jobs per site
    customers = ["Washington Co", "Jefferson Water", "Lincoln Works", "Grant Farms", "Roosevelt Drilling"]
    towns = [
        ("Corning", 39.9271, -122.1792),
        ("Orland", 39.7471, -122.1969),
        ("Chico", 39.7285, -121.8375),
        ("Cottonwood", 40.3863, -122.2803),
        ("Durham", 39.6468, -121.8005),
    ]
    cats = ["Domestic", "Ag", "Drilling", "Electrical"]
    import random
    r = random.Random(123)

    for i, cname in enumerate(customers):
        c = Customer(name=cname)
        db.session.add(c); db.session.flush()
        for s_idx in range(5):
            t = towns[(i + s_idx) % len(towns)]
            lat = t[1] + (r.random()-0.5)*0.06
            lng = t[2] + (r.random()-0.5)*0.06
            s = Site(name=f"{t[0]} Site {s_idx+1}", latitude=lat, longitude=lng, customer_id=c.id)
            db.session.add(s); db.session.flush()
            for jx, cat in enumerate(cats):
                j = Job(job_number=f"{t[0][:3].upper()}-{s_idx+1}-{jx+1}", category=cat, site_id=s.id)
                db.session.add(j)
    db.session.commit()

def _ensure_db_seeded():
    global _bootstrapped
    if _bootstrapped: 
        return
    with app.app_context():
        db.create_all()
        if not Customer.query.first():
            seed_demo()
        _bootstrapped = True

@app.before_request
def _before_any():
    _ensure_db_seeded()

# ---------- Routes ----------
@app.route("/")
def index():
    sites = Site.query.all()
    site_data = []
    for s in sites:
        jobs = [{"id": j.id, "job_number": j.job_number, "category": j.category} for j in s.jobs]
        site_data.append({
            "id": s.id, "name": s.name, "lat": s.latitude, "lng": s.longitude,
            "customer": s.customer.name, "jobs": jobs
        })
    return render_template("index.html", sites=site_data)

@app.route("/customers")
def customers():
    custs = Customer.query.order_by(Customer.name.asc()).all()
    return render_template("customers.html", customers=custs)

@app.route("/customers/<int:customer_id>")
def customer_detail(customer_id):
    c = db.session.get(Customer, customer_id)
    if not c:
        flash("Customer not found", "error")
        return redirect(url_for("customers"))
    sites = Site.query.filter_by(customer_id=c.id).order_by(Site.name.asc()).all()
    return render_template("customer_detail.html", customer=c, sites=sites)

@app.route("/sites/<int:site_id>")
def site_detail(site_id):
    s = db.session.get(Site, site_id)
    if not s:
        flash("Site not found", "error")
        return redirect(url_for("index"))
    jobs = Job.query.filter_by(site_id=s.id).order_by(Job.job_number.asc()).all()
    return render_template("site.html", site=s, jobs=jobs)

@app.route("/jobs/<int:job_id>")
def job_detail(job_id):
    j = db.session.get(Job, job_id)
    if not j:
        flash("Job not found", "error")
        return redirect(url_for("index"))
    return render_template("job.html", job=j, site=j.site)

# Health
@app.get("/healthz")
def healthz():
    return {"ok": True}, 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT","5000")), debug=True)
