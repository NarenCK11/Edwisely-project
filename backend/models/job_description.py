from datetime import datetime

from . import db


class JobDescription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hr_id = db.Column(db.Integer, db.ForeignKey("hr.id"), nullable=False)
    role_name = db.Column(db.String(200), nullable=False)
    company = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    jd_file_path = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    candidates = db.relationship(
        "Candidate",
        backref="job_description",
        lazy=True,
        cascade="all, delete-orphan",
    )

