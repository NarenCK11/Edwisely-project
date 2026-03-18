from datetime import datetime

from . import db


class Candidate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    jd_id = db.Column(
        db.Integer, db.ForeignKey("job_description.id"), nullable=False
    )
    name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(200), nullable=True)
    phone = db.Column(db.String(30), nullable=True)
    resume_file_path = db.Column(db.String(500), nullable=True)
    resume_text = db.Column(db.Text, nullable=True)

    fit_score = db.Column(db.Float, nullable=True)
    skill_match_score = db.Column(db.Float, nullable=True)
    experience_score = db.Column(db.Float, nullable=True)
    role_alignment_score = db.Column(db.Float, nullable=True)
    project_score = db.Column(db.Float, nullable=True)
    education_score = db.Column(db.Float, nullable=True)
    fit_tag = db.Column(db.String(20), nullable=True)

    matched_skills = db.Column(db.Text, nullable=True)
    missing_skills = db.Column(db.Text, nullable=True)
    strengths = db.Column(db.Text, nullable=True)
    gaps = db.Column(db.Text, nullable=True)
    suggestions = db.Column(db.Text, nullable=True)
    summary = db.Column(db.Text, nullable=True)

    is_evaluated = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

