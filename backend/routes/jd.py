from flask import current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from routes import jd_bp
from models import Candidate, HR, JobDescription, db
from services.llm_service import extract_jd_structure
from utils.pdf_utils import allowed_file, _extract_pdf_text
import os


def _error(message: str, code: str, status: int):
    return jsonify({"error": message, "code": code}), status


def _get_current_hr():
    hr_id = get_jwt_identity()
    return HR.query.get(hr_id)


@jd_bp.route("", methods=["GET"])
@jwt_required()
def list_jds():
    hr = _get_current_hr()
    if not hr:
        return _error("User not found", "NOT_FOUND", 404)

    jds = (
        JobDescription.query.filter_by(hr_id=hr.id)
        .order_by(JobDescription.created_at.desc())
        .all()
    )
    result = []
    for jd in jds:
        candidates = Candidate.query.filter_by(jd_id=jd.id).all()
        total_candidates = len(candidates)
        top_candidate = None
        if candidates:
            top_candidate = max(
                candidates, key=lambda c: c.fit_score or 0.0
            )
        result.append(
            {
                "id": jd.id,
                "role_name": jd.role_name,
                "company": jd.company,
                "description": jd.description,
                "created_at": jd.created_at.isoformat() if jd.created_at else None,
                "updated_at": jd.updated_at.isoformat() if jd.updated_at else None,
                "total_candidates": total_candidates,
                "top_candidate": {
                    "id": top_candidate.id,
                    "name": top_candidate.name,
                    "fit_score": top_candidate.fit_score,
                }
                if top_candidate and top_candidate.fit_score is not None
                else None,
            }
        )
    return jsonify(result)


@jd_bp.route("", methods=["POST"])
@jwt_required()
def create_jd():
    hr = _get_current_hr()
    if not hr:
        return _error("User not found", "NOT_FOUND", 404)

    if request.content_type and "multipart/form-data" in request.content_type:
        role_name = request.form.get("role_name", "").strip()
        company = request.form.get("company", "").strip()
        description = request.form.get("description", "").strip()
        file = request.files.get("jd_file")
    else:
        data = request.get_json() or {}
        role_name = data.get("role_name", "").strip()
        company = data.get("company", "").strip()
        description = data.get("description", "").strip()
        file = None

    if not role_name or not company or (not description and not file):
        return _error("Missing required fields", "VALIDATION_ERROR", 400)

    jd = JobDescription(
        hr_id=hr.id,
        role_name=role_name,
        company=company,
        description=description or "",
    )
    db.session.add(jd)
    db.session.flush()

    if file:
        if not allowed_file(file.filename):
            return _error("Only PDF and TXT allowed", "INVALID_FILE_TYPE", 400)
        upload_root = current_app.config["UPLOAD_FOLDER"]
        jd_dir = os.path.join(upload_root, "jd")
        os.makedirs(jd_dir, exist_ok=True)
        ext = file.filename.rsplit(".", 1)[1].lower()
        filename = f"{jd.id}.{ext}"
        file_path = os.path.join(jd_dir, filename)
        file.save(file_path)
        jd.jd_file_path = file_path
        if ext == "pdf":
            try:
                description_text = _extract_pdf_text(file_path)
            except Exception:
                description_text = ""
        else:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                description_text = f.read()
        if description_text:
            jd.description = description_text

    db.session.commit()

    return (
        jsonify(
            {
                "id": jd.id,
                "role_name": jd.role_name,
                "company": jd.company,
                "description": jd.description,
                "created_at": jd.created_at.isoformat()
                if jd.created_at
                else None,
                "jd_file_path": jd.jd_file_path,
            }
        ),
        201,
    )


@jd_bp.route("/<int:jd_id>", methods=["GET"])
@jwt_required()
def get_jd(jd_id: int):
    hr = _get_current_hr()
    if not hr:
        return _error("User not found", "NOT_FOUND", 404)

    jd = JobDescription.query.get(jd_id)
    if not jd or jd.hr_id != hr.id:
        return _error("Job description not found", "NOT_FOUND", 404)

    return jsonify(
        {
            "id": jd.id,
            "role_name": jd.role_name,
            "company": jd.company,
            "description": jd.description,
            "created_at": jd.created_at.isoformat()
            if jd.created_at
            else None,
            "updated_at": jd.updated_at.isoformat()
            if jd.updated_at
            else None,
        }
    )


@jd_bp.route("/<int:jd_id>", methods=["PUT"])
@jwt_required()
def update_jd(jd_id: int):
    hr = _get_current_hr()
    if not hr:
        return _error("User not found", "NOT_FOUND", 404)

    jd = JobDescription.query.get(jd_id)
    if not jd or jd.hr_id != hr.id:
        return _error("Job description not found", "NOT_FOUND", 404)

    data = request.get_json() or {}
    role_name = data.get("role_name")
    company = data.get("company")
    description = data.get("description")

    if role_name:
        jd.role_name = role_name.strip()
    if company:
        jd.company = company.strip()
    if description is not None:
        jd.description = description

    db.session.commit()

    return jsonify(
        {
            "id": jd.id,
            "role_name": jd.role_name,
            "company": jd.company,
            "description": jd.description,
            "created_at": jd.created_at.isoformat()
            if jd.created_at
            else None,
            "updated_at": jd.updated_at.isoformat()
            if jd.updated_at
            else None,
        }
    )


@jd_bp.route("/<int:jd_id>", methods=["DELETE"])
@jwt_required()
def delete_jd(jd_id: int):
    hr = _get_current_hr()
    if not hr:
        return _error("User not found", "NOT_FOUND", 404)

    jd = JobDescription.query.get(jd_id)
    if not jd or jd.hr_id != hr.id:
        return _error("Job description not found", "NOT_FOUND", 404)

    db.session.delete(jd)
    db.session.commit()
    return jsonify({"message": "Deleted"}), 200

