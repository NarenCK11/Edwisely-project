import logging
import os

from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import jwt_required

from config import DevelopmentConfig
from models import db
from routes import auth_bp, candidates_bp, jd_bp
from routes.auth import jwt
from models.hr import HR


def create_app(config_class=DevelopmentConfig):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Extensions
    db.init_app(app)
    jwt.init_app(app)

    # CORS
    # Allow frontend origins to access the backend.
    # Set CORS_ORIGINS to a comma-separated list (e.g. "http://localhost:5173,https://your-frontend.com").
    cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173")
    CORS(
        app,
        origins=[o.strip() for o in cors_origins.split(",") if o.strip()],
        supports_credentials=True,
    )

    # Blueprints
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(jd_bp, url_prefix="/api/jd")
    app.register_blueprint(candidates_bp)

    # Create database and seed demo HR on first run
    with app.app_context():
        db.create_all()
        if HR.query.count() == 0:
            demo = HR(
                name="Demo HR",
                email="demo@hrportal.com",
                phone_number=None,
            )
            demo.set_password("Demo@1234")
            db.session.add(demo)
            db.session.commit()
            print(
                "Demo account created: demo@hrportal.com / Demo@1234"
            )

    # Consistent JSON error handlers
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({"error": "Bad request", "code": "BAD_REQUEST"}), 400

    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify(
            {"error": "Unauthorized", "code": "UNAUTHORIZED"}
        ), 401

    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({"error": "Forbidden", "code": "FORBIDDEN"}), 403

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Not found", "code": "NOT_FOUND"}), 404

    @app.errorhandler(500)
    def internal_error(error):
        logging.exception("Internal server error: %s", error)
        return (
            jsonify(
                {"error": "Internal server error", "code": "SERVER_ERROR"}
            ),
            500,
        )

    return app


if __name__ == "__main__":
    app = create_app()
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

