The user just wants the documentation text optimized — no need for a docx file. I'll rewrite it directly.

Here's the optimized documentation — tighter, no redundancy:

---

# Project Documentation

## Overview

AI-powered resume evaluation app for HR teams to manage job descriptions, ingest resumes, and rank candidates using rule-based scoring + LLM evaluation.

- **Backend**: Python + Flask + SQLAlchemy + JWT + PDF parsing
- **Frontend**: React (Vite) + Tailwind + Axios + React Router
- **LLM Service**: Multi-provider (Groq / Mistral / OpenRouter) with automatic fallback
- **Database**: SQLite via SQLAlchemy ORM (configurable)

---

## 1. Project Structure

```
backend/
  app.py          # Flask app factory + error handlers
  config.py       # Config + env var defaults
  models/         # SQLAlchemy ORM models
  routes/         # Blueprints: auth, JDs, candidates
  services/       # LLM + scoring logic
  utils/          # PDF extraction, file upload helpers
frontend/
  src/            # Pages, components, API client, auth context
```

---

## 2. Backend

### 2.1 Startup (`app.py`)

Flask app factory pattern. Initializes SQLAlchemy, JWT, and CORS (`http://localhost:5173`). Registers blueprints at `/api/auth`, `/api/jd`, and `/api/jd/<id>/candidates`. Seeds a demo HR account (`demo@hrportal.com`) on first run.

### 2.2 Configuration (`config.py`)

| Variable | Default |
|---|---|
| `SECRET_KEY`, `JWT_SECRET_KEY` | — |
| `SQLALCHEMY_DATABASE_URI` | `sqlite:///resume_evaluator.db` |
| `UPLOAD_FOLDER` | `backend/uploads/` |
| `MAX_CONTENT_LENGTH` | 5 MiB |
| `GEMINI_API_KEY`, `GEMINI_MODEL` | `gemini-2.5-flash` |

### 2.3 Models

**`HR`** — `id`, `name`, `email`, `phone_number`, `password_hash`, `created_at`. Has many `JobDescription`. Passwords hashed via `werkzeug`.

**`JobDescription`** — `id`, `hr_id`, `role_name`, `company`, `description`, `jd_file_path`, timestamps. Has many `Candidate`.

**`Candidate`** — Profile metadata + evaluation results: `resume_file_path`, `resume_text`, `fit_score`, component scores (`skill_match_score`, `experience_score`, etc.), `fit_tag` (`Excellent`/`Good`/`Poor`), JSON fields for `matched_skills`, `missing_skills`, `strengths`, `gaps`, `suggestions`, `summary`, `is_evaluated`.

---

## 3. API Routes

All endpoints require JWT except signup/login.

### Auth (`/api/auth`)

| Endpoint | Method | Description |
|---|---|---|
| `/signup` | POST | Create account, return JWT + profile |
| `/login` | POST | Authenticate, return JWT + profile |
| `/me` | GET | Get current HR profile |
| `/me` | PUT | Update name / phone |

### Job Descriptions (`/api/jd`)

| Endpoint | Method | Description |
|---|---|---|
| `/api/jd` | GET | List JDs with candidate count + top scorer |
| `/api/jd` | POST | Create JD (JSON or multipart with PDF/TXT) |
| `/api/jd/<id>` | GET/PUT/DELETE | Get, update, or delete a JD |

JD files stored at `backend/uploads/jd/<id>.<ext>`. PDF text extracted via `pdfplumber`.

### Candidates (`/api/jd/<jd_id>/candidates`)

| Endpoint | Method | Description |
|---|---|---|
| `/candidates` | GET | List candidates sorted by score; supports `?search=` |
| `/candidates` | POST | Upload resume + optionally evaluate immediately |
| `/candidates/<id>` | GET/PUT/DELETE | Get, update, or delete a candidate |
| `/candidates/<id>/evaluate` | POST | Run LLM + rule-based evaluation |
| `/candidates/evaluate-all` | POST | Evaluate all unevaluated candidates |

Resumes stored at `backend/uploads/resumes/<jd_id>/<candidate_id>.<ext>`. Extracted text saved to DB.

---

## 4. LLM & Scoring (`services/llm_service.py`)

### Provider Fallback

Tries providers in order; falls back on 429/rate-limit errors:
1. **Groq** (fast, high volume)
2. **Mistral** (large free quota)
3. **OpenRouter** (many models)

All use the OpenAI-compatible API format.

### Evaluation Pipeline (`evaluate_candidate`)

1. **Rule-based** (no API call): extract skills and experience from JD + resume → compute `skill_match_score` (40 pts) and `experience_depth_score` (25 pts).
2. **LLM scoring**: JSON-only prompt → `role_alignment_score` (20), `project_strength_score` (10), `education_bonus_score` (5), plus `strengths`, `gaps`, `suggestions`, `summary`.
3. **Stabilization**: clamp scores, recompute `total_score` and `fit_tag` (`Excellent` ≥ 75, `Good` ≥ 50, else `Poor`).
4. **Fallback**: if LLM fails, return rule-based partial scores.

### Rule-based Helpers

- `_quick_extract_jd` — required/preferred skills + minimum years from JD text
- `_quick_extract_skills` — tech keywords from resume text
- `_compute_experience_score` — heuristic from date ranges

---

## 5. Frontend

React + Vite thin client. All API calls go through `src/api/axios.js` (base URL from `VITE_API_BASE_URL`, auto-attaches JWT; redirects to `/login` on 401).

**Auth**: JWT stored in `localStorage`, managed via `AuthContext`.

**Pages**: Login, Signup, Dashboard (JD list), Job Detail (candidates, upload, evaluate).

**Key components**: `JDCard`, `CandidateCard`, `AddJDModal`, `AddCandidateModal`, `ScoreBreakdown` (recharts bar chart), `TopScorerBanner`.

---

## 6. Running Locally

**Backend**
```bash
cd backend
python -m venv venv && source venv/bin/activate  # or venv\Scripts\Activate.ps1 on Windows
pip install -r requirements.txt
# Create .env with keys from config.py
python app.py
```

**Frontend**
```bash
cd frontend
npm install
# .env: VITE_API_BASE_URL=http://localhost:5000
npm run dev
```

---

## 7. Extending

- **LLM providers**: Edit `PROVIDERS` list in `llm_service.py`.
- **Production DB**: Set `DATABASE_URL=postgresql://user:pass@host:5432/resume_evaluator`.
- **Scoring accuracy**: Adjust `WEIGHTS`, refine `_USER_TEMPLATE` prompt, or add NLP parsing (spaCy/regex) to extraction helpers.

---

## 8. Troubleshooting

- DB and uploads default to `backend/` directory.
- On `429` errors: wait for quota reset or add another provider key in `.env`.
- Never commit `SECRET_KEY` or `JWT_SECRET_KEY` to source control.