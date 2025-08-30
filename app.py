import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from datetime import datetime

app = Flask(__name__)
app.secret_key = "supersecret"
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///wellatlas.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    sites = db.relationship("Site", backref="customer", lazy=True)

class Site(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey("customer.id"), nullable=False)
    jobs = db.relationship("Job", backref="site", lazy=True)

class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_number = db.Column(db.String(50), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    site_id = db.Column(db.Integer, db.ForeignKey("site.id"), nullable=False)
    entries = db.relationship("Entry", backref="job", lazy=True)

class Entry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    job_id = db.Column(db.Integer, db.ForeignKey("job.id"), nullable=False)
    created_by = db.Column(db.String(150), nullable=True)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.before_first_request
def init_db():
    db.create_all()
    if not User.query.first():
        db.session.add(User(username="admin", password="password"))
        db.session.commit()
    if not Customer.query.first():
        seed_data()

def seed_data():
    presidents = ["Washington", "Adams", "Jefferson", "Madison", "Monroe"]
    coords = [(39.93,-122.18), (39.74,-122.19), (39.73,-121.84), (40.38,-122.28), (39.64,-121.80)]
    for i, pres in enumerate(presidents):
        cust = Customer(name=pres)
        db.session.add(cust)
        db.session.commit()
        for s in range(5):
            lat, lng = coords[i]
            site = Site(name=f"{pres} Site {s+1}", latitude=lat+0.01*s, longitude=lng-0.01*s, customer_id=cust.id)
            db.session.add(site)
            db.session.commit()
            job = Job(job_number=f"J{pres[0]}{s+1}", category=["Domestic","Ag","Drilling","Electrical"][s%4], site_id=site.id)
            db.session.add(job)
            db.session.commit()
            for d in range(3):
                entry = Entry(text=f"Entry {d+1} for {job.job_number}", job_id=job.id, created_by="admin")
                db.session.add(entry)
    db.session.commit()

@app.route("/")
def index():
    sites = Site.query.all()
    return render_template("index.html", sites=sites)

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form["username"]).first()
        if user and user.password == request.form["password"]:
            login_user(user)
            return redirect(url_for("index"))
        else:
            flash("Invalid credentials")
    return render_template("login.html")

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)
