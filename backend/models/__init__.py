from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from .hr import HR  # noqa: E402,F401
from .job_description import JobDescription  # noqa: E402,F401
from .candidate import Candidate  # noqa: E402,F401

