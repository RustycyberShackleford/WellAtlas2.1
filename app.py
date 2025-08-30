\
import os
import random
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash
from models import db, Customer, Site, Job, TimelineEntry

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "dev-secret")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///wellatlas.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

# --------- Utilities ----------

def seed_if_empty():
    with app.app_context():
        if Customer.query.first():
            return  # already seeded
        presidents = ["Washington", "Lincoln", "Jefferson", "Roosevelt", "Kennedy"]
        towns = [
            ("Corning", 39.9271, -122.1792),
            ("Orland", 39.7471, -122.1969),
            ("Chico", 39.7285, -121.8375),
            ("Cottonwood", 40.3863, -122.2803),
            ("Durham", 39.6468, -121.8005),
        ]
        cats = ["Domestic", "Ag", "Drilling", "Electrical"]
        rnd = random.Random(42)
        for p in presidents:
            cust = Customer(name=f"{p} Water Co")
            db.session.add(cust); db.session.flush()
            for si in range(10):
                town = towns[(si) % len(towns)]
                lat = town[1] + (rnd.random()-0.5)*0.08
                lng = town[2] + (rnd.random()-0.5)*0.08
                site = Site(
                    name=f"{town[0]} Site {si+1}",
                    latitude=lat, longitude=lng,
                    customer_id=cust.id
                )
                db.session.add(site); db.session.flush()
                for c in cats:
                    job = Job(
                        job_number=f"{town[0][:3].upper()}-{si+1}-{c[:3].upper()}",
                        category=c, status="Open", site_id=site.id
                    )
                    db.session.add(job); db.session.flush()
                    # add a couple timeline entries across days
                    now = datetime.utcnow()
                    for k in range(2):
                        e = TimelineEntry(job_id=job.id,
                                          when=now - timedelta(days=(k+1)),
                                          text=f"{c} work log day {k+1} at {site.name}")
                        db.session.add(e)
        db.session.commit()

@app.before_request
def _ensure_db():
    db.create_all()
    seed_if_empty()

# --------- Routes ----------

@app.get("/")
def index():
    # map + pins
    maptile_key = os.getenv("MAPTILER_KEY", "")
    # minimal site payload for map (and near-me filter)
    sites = []
    for s in Site.query.all():
        sites.append({
            "id": s.id,
            "name": s.name,
            "lat": s.latitude,
            "lng": s.longitude,
            "customer": s.customer.name
        })
    return render_template("index.html", MAPTILER_KEY=maptile_key, sites=sites)

@app.get("/healthz")
def healthz():
    return {"ok": True}, 200

# Customers
@app.get("/customers")
def customers():
    cs = Customer.query.order_by(Customer.name.asc()).all()
    return render_template("customers.html", customers=cs)

@app.get("/customers/new")
def new_customer():
    return render_template("customer_new.html")

@app.post("/customers/create")
def create_customer():
    name = request.form.get("name","").strip()
    if not name:
        flash("Customer name required", "error")
        return redirect(url_for("new_customer"))
    c = Customer(name=name)
    db.session.add(c); db.session.commit()
    flash("Customer created", "ok")
    return redirect(url_for("customers"))

@app.post("/customers/<int:cid>/delete")
def delete_customer(cid):
    c = db.session.get(Customer, cid)
    if not c:
        flash("Not found", "error")
        return redirect(url_for("customers"))
    db.session.delete(c); db.session.commit()
    flash("Customer deleted", "ok")
    return redirect(url_for("customers"))

@app.get("/customers/<int:cid>")
def customer_detail(cid):
    c = db.session.get(Customer, cid)
    if not c:
        flash("Not found", "error")
        return redirect(url_for("customers"))
    sites = Site.query.filter_by(customer_id=cid).order_by(Site.name.asc()).all()
    return render_template("customer_detail.html", customer=c, sites=sites)

# Sites
@app.get("/sites/new")
def new_site():
    # expects ?customer_id=
    customer_id = request.args.get("customer_id", type=int)
    customers = Customer.query.order_by(Customer.name.asc()).all()
    return render_template("site_new.html", customers=customers, selected_customer=customer_id)

@app.post("/sites/create")
def create_site():
    name = request.form.get("name","").strip()
    lat = request.form.get("latitude", type=float)
    lng = request.form.get("longitude", type=float)
    customer_id = request.form.get("customer_id", type=int)
    if not (name and lat is not None and lng is not None and customer_id):
        flash("All fields required", "error")
        return redirect(url_for("new_site"))
    s = Site(name=name, latitude=lat, longitude=lng, customer_id=customer_id)
    db.session.add(s); db.session.commit()
    flash("Site created", "ok")
    return redirect(url_for("customer_detail", cid=customer_id))

@app.post("/sites/<int:sid>/delete")
def delete_site(sid):
    s = db.session.get(Site, sid)
    if not s:
        flash("Not found", "error")
        return redirect(url_for("customers"))
    cid = s.customer_id
    db.session.delete(s); db.session.commit()
    flash("Site deleted", "ok")
    return redirect(url_for("customer_detail", cid=cid))

@app.get("/sites/<int:sid>")
def site_detail(sid):
    s = db.session.get(Site, sid)
    if not s:
        flash("Not found", "error")
        return redirect(url_for("customers"))
    jobs = Job.query.filter_by(site_id=sid).order_by(Job.job_number.asc()).all()
    return render_template("site.html", site=s, jobs=jobs)

# Jobs
@app.get("/jobs/new")
def new_job():
    # expects ?site_id=
    site_id = request.args.get("site_id", type=int)
    sites = Site.query.order_by(Site.name.asc()).all()
    categories = ["Domestic","Ag","Drilling","Electrical"]
    return render_template("job_new.html", sites=sites, selected_site=site_id, categories=categories)

@app.post("/jobs/create")
def create_job():
    site_id = request.form.get("site_id", type=int)
    job_number = request.form.get("job_number","").strip()
    category = request.form.get("category","").strip()
    status = request.form.get("status","Open").strip() or "Open"
    if not (site_id and job_number and category):
        flash("All fields required", "error")
        return redirect(url_for("new_job"))
    j = Job(site_id=site_id, job_number=job_number, category=category, status=status)
    db.session.add(j); db.session.commit()
    flash("Job created", "ok")
    return redirect(url_for("site_detail", sid=site_id))

@app.post("/jobs/<int:jid>/delete")
def delete_job(jid):
    j = db.session.get(Job, jid)
    if not j:
        flash("Not found", "error")
        return redirect(url_for("customers"))
    sid = j.site_id
    db.session.delete(j); db.session.commit()
    flash("Job deleted", "ok")
    return redirect(url_for("site_detail", sid=sid))

@app.get("/jobs/<int:jid>")
def job_detail(jid):
    j = db.session.get(Job, jid)
    if not j:
        flash("Not found", "error")
        return redirect(url_for("customers"))
    entries = TimelineEntry.query.filter_by(job_id=jid).order_by(TimelineEntry.when.desc()).all()
    return render_template("job.html", job=j, entries=entries)

@app.post("/jobs/<int:jid>/entries/create")
def add_entry(jid):
    j = db.session.get(Job, jid)
    if not j:
        flash("Not found", "error")
        return redirect(url_for("customers"))
    text = request.form.get("text","").strip()
    when_str = request.form.get("when","").strip()
    when = datetime.utcnow()
    if when_str:
        try:
            when = datetime.fromisoformat(when_str)
        except Exception:
            pass
    if not text:
        flash("Entry text required", "error")
        return redirect(url_for("job_detail", jid=jid))
    e = TimelineEntry(job_id=jid, when=when, text=text)
    db.session.add(e); db.session.commit()
    flash("Timeline entry added", "ok")
    return redirect(url_for("job_detail", jid=jid))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        seed_if_empty()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT","5000")), debug=True)
