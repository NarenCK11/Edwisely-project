from flask import Blueprint

auth_bp = Blueprint("auth", __name__)
jd_bp = Blueprint("jd", __name__)
candidates_bp = Blueprint("candidates", __name__)

from . import auth, jd, candidates  # noqa: E402,F401

