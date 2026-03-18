from flask import jsonify, request
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    get_jwt_identity,
    jwt_required,
)

from routes import auth_bp
from models import db, HR


jwt = JWTManager()


def _error(message: str, code: str, status: int):
    return jsonify({"error": message, "code": code}), status


@auth_bp.route("/signup", methods=["POST"])
def signup():
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    phone = data.get("phone_number") or data.get("phone")
    password = data.get("password")

    if not name or not email or not password:
        return _error("Missing required fields", "VALIDATION_ERROR", 400)

    if HR.query.filter_by(email=email).first():
        return _error("Email already registered", "EMAIL_TAKEN", 400)

    hr = HR(name=name, email=email, phone_number=phone)
    hr.set_password(password)
    db.session.add(hr)
    db.session.commit()

    access_token = create_access_token(identity=str(hr.id))
    return (
        jsonify(
            {
                "access_token": access_token,
                "hr": {
                    "id": hr.id,
                    "name": hr.name,
                    "email": hr.email,
                    "phone_number": hr.phone_number,
                },
            }
        ),
        201,
    )


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password")

    if not email or not password:
        return _error("Email and password required", "VALIDATION_ERROR", 400)

    hr = HR.query.filter_by(email=email).first()
    if not hr or not hr.check_password(password):
        return _error("Invalid credentials", "INVALID_CREDENTIALS", 401)

    access_token = create_access_token(identity=str(hr.id))
    return jsonify(
        {
            "access_token": access_token,
            "hr": {
                "id": hr.id,
                "name": hr.name,
                "email": hr.email,
                "phone_number": hr.phone_number,
            },
        }
    )


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    hr_id = get_jwt_identity()
    hr = HR.query.get(hr_id)
    if not hr:
        return _error("User not found", "NOT_FOUND", 404)

    return jsonify(
        {
            "id": hr.id,
            "name": hr.name,
            "email": hr.email,
            "phone_number": hr.phone_number,
        }
    )


@auth_bp.route("/me", methods=["PUT"])
@jwt_required()
def update_me():
    hr_id = get_jwt_identity()
    hr = HR.query.get(hr_id)
    if not hr:
        return _error("User not found", "NOT_FOUND", 404)

    data = request.get_json() or {}
    name = data.get("name")
    phone = data.get("phone_number") or data.get("phone")

    if name:
        hr.name = name.strip()
    if phone is not None:
        hr.phone_number = phone

    db.session.commit()
    return jsonify(
        {
            "id": hr.id,
            "name": hr.name,
            "email": hr.email,
            "phone_number": hr.phone_number,
        }
    )

