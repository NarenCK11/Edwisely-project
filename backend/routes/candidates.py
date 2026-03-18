import json
from typing import List, Optional

from flask import jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from routes import candidates_bp
from models import Candidate, HR, JobDescription, db
from services.llm_service import (
    extract_jd_structure,
    extract_resume_structure,
    score_candidate,
)
from utils.pdf_utils import save_and_extract_resume


def _error(message: str, code: str, status: int):
    return jsonify({"error": message, "code": code}), status


def _get_current_hr():
    hr_id = get_jwt_identity()
    return HR.query.get(hr_id)


def _compute_fit_tag(score: Optional[float]) -> Optional[str]:
    if score is None:
        return None
    if score >= 75:
        return "Excellent"
    if score >= 50:
        return "Good"
    return "Poor"


def _ensure_ownership(jd_id: int, hr: HR) -> Optional[JobDescription]:
    jd = JobDescription.query.get(jd_id)
    if not jd or jd.hr_id != hr.id:
        return None
    return jd


def _evaluate_candidate(candidate: Candidate, jd: JobDescription) -> bool:
    """Run LLM-based evaluation for a single candidate. Returns True on success."""
    if not candidate.resume_text or not jd.description:
        return False

    jd_json = extract_jd_structure(jd.description)
    resume_json = extract_resume_structure(candidate.resume_text)
    if not jd_json or not resume_json:
        return False

    scoring = score_candidate(resume_json, jd_json)
    if not scoring:
        return False

    candidate.skill_match_score = scoring.get("skill_match_score")
    candidate.experience_score = scoring.get("experience_depth_score")
    candidate.role_alignment_score = scoring.get("role_alignment_score")
    candidate.project_score = scoring.get("project_strength_score")
    candidate.education_score = scoring.get("education_bonus_score")
    candidate.fit_score = scoring.get("total_score")
    candidate.fit_tag = _compute_fit_tag(candidate.fit_score)

    for key in ["matched_skills", "missing_skills", "strengths", "gaps", "suggestions"]:
        value = scoring.get(key) or []
        setattr(candidate, key, json.dumps(value, ensure_ascii=False))

    candidate.summary = scoring.get("summary")
    candidate.is_evaluated = True
    return True


@candidates_bp.route("/api/jd/<int:jd_id>/candidates", methods=["GET"])
@jwt_required()
def list_candidates(jd_id: int):
    hr = _get_current_hr()
    if not hr:
        return _error("User not found", "NOT_FOUND", 404)

    jd = _ensure_ownership(jd_id, hr)
    if not jd:
        return _error("Job description not found", "NOT_FOUND", 404)

    search = request.args.get("search", "").strip().lower()

    query = Candidate.query.filter_by(jd_id=jd.id)
    candidates: List[Candidate] = query.all()

    if search:
        candidates = [
            c
            for c in candidates
            if search in (c.name or "").lower()
            or search in (c.email or "").lower()
        ]

    candidates.sort(key=lambda c: (c.fit_score or 0.0), reverse=True)

    result = []
    for idx, c in enumerate(candidates, start=1):
        result.append(
            {
                "id": c.id,
                "rank": idx,
                "name": c.name,
                "email": c.email,
                "phone": c.phone,
                "fit_score": c.fit_score,
                "fit_tag": c.fit_tag,
                "is_evaluated": c.is_evaluated,
            }
        )
    return jsonify(result)


@candidates_bp.route("/api/jd/<int:jd_id>/candidates", methods=["POST"])
@jwt_required()
def create_candidate(jd_id: int):
    hr = _get_current_hr()
    if not hr:
        return _error("User not found", "NOT_FOUND", 404)

    jd = _ensure_ownership(jd_id, hr)
    if not jd:
        return _error("Job description not found", "NOT_FOUND", 404)

    if not request.content_type or "multipart/form-data" not in request.content_type:
        return _error("Multipart form required", "VALIDATION_ERROR", 400)

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip() or None
    phone = request.form.get("phone", "").strip() or None
    evaluate_immediately = request.form.get("evaluate_immediately") == "true"
    file = request.files.get("resume")

    if not name or not file:
        return _error("Name and resume are required", "VALIDATION_ERROR", 400)

    candidate = Candidate(
        jd_id=jd.id,
        name=name,
        email=email,
        phone=phone,
    )
    db.session.add(candidate)
    db.session.flush()

    try:
        file_path, text = save_and_extract_resume(
            file_storage=file,
            subdir=f"resumes/{jd.id}",
            target_filename=str(candidate.id),
        )
    except ValueError as exc:
        db.session.rollback()
        return _error(str(exc), "FILE_ERROR", 400)
    except Exception:
        db.session.rollback()
        return _error(
            "Failed to save or process resume", "FILE_ERROR", 500
        )

    candidate.resume_file_path = file_path
    candidate.resume_text = text

    if evaluate_immediately:
        if not _evaluate_candidate(candidate, jd):
            # Do not fail creation; mark unevaluated
            candidate.is_evaluated = False

    db.session.commit()

    return (
        jsonify(
            {
                "id": candidate.id,
                "name": candidate.name,
                "email": candidate.email,
                "phone": candidate.phone,
                "fit_score": candidate.fit_score,
                "fit_tag": candidate.fit_tag,
                "is_evaluated": candidate.is_evaluated,
            }
        ),
        201,
    )


@candidates_bp.route(
    "/api/jd/<int:jd_id>/candidates/<int:candidate_id>", methods=["GET"]
)
@jwt_required()
def get_candidate(jd_id: int, candidate_id: int):
    hr = _get_current_hr()
    if not hr:
        return _error("User not found", "NOT_FOUND", 404)

    jd = _ensure_ownership(jd_id, hr)
    if not jd:
        return _error("Job description not found", "NOT_FOUND", 404)

    candidate = Candidate.query.get(candidate_id)
    if not candidate or candidate.jd_id != jd.id:
        return _error("Candidate not found", "NOT_FOUND", 404)

    def _loads(text: Optional[str]):
        if not text:
            return []
        try:
            return json.loads(text)
        except Exception:
            return []

    return jsonify(
        {
            "id": candidate.id,
            "jd_id": candidate.jd_id,
            "name": candidate.name,
            "email": candidate.email,
            "phone": candidate.phone,
            "fit_score": candidate.fit_score,
            "skill_match_score": candidate.skill_match_score,
            "experience_score": candidate.experience_score,
            "role_alignment_score": candidate.role_alignment_score,
            "project_score": candidate.project_score,
            "education_score": candidate.education_score,
            "fit_tag": candidate.fit_tag,
            "matched_skills": _loads(candidate.matched_skills),
            "missing_skills": _loads(candidate.missing_skills),
            "strengths": _loads(candidate.strengths),
            "gaps": _loads(candidate.gaps),
            "suggestions": _loads(candidate.suggestions),
            "summary": candidate.summary,
            "is_evaluated": candidate.is_evaluated,
            "created_at": candidate.created_at.isoformat()
            if candidate.created_at
            else None,
        }
    )


@candidates_bp.route(
    "/api/jd/<int:jd_id>/candidates/<int:candidate_id>", methods=["PUT"]
)
@jwt_required()
def update_candidate(jd_id: int, candidate_id: int):
    hr = _get_current_hr()
    if not hr:
        return _error("User not found", "NOT_FOUND", 404)

    jd = _ensure_ownership(jd_id, hr)
    if not jd:
        return _error("Job description not found", "NOT_FOUND", 404)

    candidate = Candidate.query.get(candidate_id)
    if not candidate or candidate.jd_id != jd.id:
        return _error("Candidate not found", "NOT_FOUND", 404)

    data = request.get_json() or {}
    for field in ["name", "email", "phone"]:
        if field in data:
            setattr(candidate, field, data[field])

    db.session.commit()
    return jsonify(
        {
            "id": candidate.id,
            "name": candidate.name,
            "email": candidate.email,
            "phone": candidate.phone,
        }
    )


@candidates_bp.route(
    "/api/jd/<int:jd_id>/candidates/<int:candidate_id>", methods=["DELETE"]
)
@jwt_required()
def delete_candidate(jd_id: int, candidate_id: int):
    hr = _get_current_hr()
    if not hr:
        return _error("User not found", "NOT_FOUND", 404)

    jd = _ensure_ownership(jd_id, hr)
    if not jd:
        return _error("Job description not found", "NOT_FOUND", 404)

    candidate = Candidate.query.get(candidate_id)
    if not candidate or candidate.jd_id != jd.id:
        return _error("Candidate not found", "NOT_FOUND", 404)

    db.session.delete(candidate)
    db.session.commit()
    return jsonify({"message": "Deleted"}), 200


@candidates_bp.route(
    "/api/jd/<int:jd_id>/candidates/<int:candidate_id>/evaluate",
    methods=["POST"],
)
@jwt_required()
def evaluate_candidate_route(jd_id: int, candidate_id: int):
    hr = _get_current_hr()
    if not hr:
        return _error("User not found", "NOT_FOUND", 404)

    jd = _ensure_ownership(jd_id, hr)
    if not jd:
        return _error("Job description not found", "NOT_FOUND", 404)

    candidate = Candidate.query.get(candidate_id)
    if not candidate or candidate.jd_id != jd.id:
        return _error("Candidate not found", "NOT_FOUND", 404)

    ok = _evaluate_candidate(candidate, jd)
    if not ok:
        db.session.commit()
        return _error(
            "Evaluation failed – please retry", "EVALUATION_FAILED", 500
        )

    db.session.commit()
    return jsonify({"message": "Evaluated", "fit_score": candidate.fit_score})


@candidates_bp.route(
    "/api/jd/<int:jd_id>/candidates/evaluate-all", methods=["POST"]
)
@jwt_required()
def evaluate_all_candidates(jd_id: int):
    hr = _get_current_hr()
    if not hr:
        return _error("User not found", "NOT_FOUND", 404)

    jd = _ensure_ownership(jd_id, hr)
    if not jd:
        return _error("Job description not found", "NOT_FOUND", 404)

    candidates = Candidate.query.filter_by(
        jd_id=jd.id, is_evaluated=False
    ).all()
    success_count = 0
    for candidate in candidates:
        if _evaluate_candidate(candidate, jd):
            success_count += 1

    db.session.commit()
    return jsonify(
        {"message": "Evaluation completed", "evaluated_count": success_count}
    )

