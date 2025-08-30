from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Customer(db.Model):
    __tablename__ = "customers"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, unique=True)
    sites = db.relationship("Site", backref="customer", cascade="all, delete-orphan")

class Site(db.Model):
    __tablename__ = "sites"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=False)
    jobs = db.relationship("Job", backref="site", cascade="all, delete-orphan")

class Job(db.Model):
    __tablename__ = "jobs"
    id = db.Column(db.Integer, primary_key=True)
    job_number = db.Column(db.String(50), nullable=False)
    category = db.Column(db.String(50), nullable=False)  # Domestic, Ag, Drilling, Electrical
    status = db.Column(db.String(50), default="Open")
    site_id = db.Column(db.Integer, db.ForeignKey("sites.id"), nullable=False)
    entries = db.relationship("TimelineEntry", backref="job", cascade="all, delete-orphan")

class TimelineEntry(db.Model):
    __tablename__ = "timeline_entries"
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id"), nullable=False)
    when = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    text = db.Column(db.Text, nullable=False)
