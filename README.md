## AI-Powered Resume Evaluator

Full-stack web app for HR teams to upload job descriptions and resumes, then rank candidates using a hybrid **rule-based + Gemini LLM** scoring engine.

### Tech Stack

- **Backend**: Python, Flask, Flask-SQLAlchemy, Flask-JWT-Extended, Flask-CORS, pdfplumber, google-generativeai
- **Frontend**: React (Vite-style), React Router v6, Axios, Recharts
- **Database**: SQLite via SQLAlchemy ORM
- **LLM**: Google Gemini 2.5 Flash

---

## 1. Prerequisites

- **Python**: 3.10+ (3.12 tested)
- **Node.js**: 18+ (20+ recommended for Vite)
- **npm**: 9+

You also need a free Gemini API key from [Google AI Studio](https://aistudio.google.com).

---

## 2. Backend Setup

From the project root:

```bash
cd backend
python -m venv venv
```

Activate the virtual environment:

- **Windows (PowerShell)**
  ```bash
  venv\Scripts\Activate.ps1
  ```
- **macOS / Linux**
  ```bash
  source venv/bin/activate
  ```

Install dependencies:

```bash
pip install -r requirements.txt
```

### 2.1 Environment variables

Create `backend/.env` (already present in this repo; adjust values as needed):

```env
FLASK_ENV=development
SECRET_KEY=change-me-in-production
JWT_SECRET_KEY=change-jwt-secret
GEMINI_API_KEY=your-gemini-key-here
GEMINI_MODEL=gemini-2.5-flash
DATABASE_URL=sqlite:///resume_evaluator.db
UPLOAD_FOLDER=uploads
MAX_CONTENT_LENGTH=5242880
```

Replace `your-gemini-key-here` with the key from Google AI Studio.

### 2.2 Run the backend

From the `backend` directory with the venv activated:

```bash
python app.py
```

The API will start on `http://localhost:5000`.

On first run, a demo HR account is created:

- **Email**: `demo@hrportal.com`
- **Password**: `Demo@1234`

---

## 3. Frontend Setup

From the project root:

```bash
cd frontend
npm install
```

Create `frontend/.env`:

```env
VITE_API_BASE_URL=http://localhost:5000
```

### 3.1 Run the frontend

From the `frontend` directory:

```bash
npm run dev
```

The app will be available at `http://localhost:5173`.

---

## 4. Core Features

- **Authentication**
  - HR signup, login, and profile (JWT-based).
  - JWT stored in `localStorage`, auto-attached via Axios interceptor.

- **Job Descriptions Dashboard**
  - View all JDs for the logged-in HR.
  - Add new JD via text or PDF upload.
  - See candidate counts and top candidate per JD.

- **JD Detail Page**
  - Full JD text (collapsible).
  - Top scorer banner with fit score, tag, and key skills.
  - Candidate list sorted by fit score, with search and inline details.
  - Upload candidate resumes (PDF/TXT) and evaluate individually or in bulk.

- **Scoring & Visualisation**
  - Hybrid rule-based + LLM scoring for:
    - Skill Match, Experience Depth, Role Alignment, Project Strength, Education Bonus.
  - Total fit score (0–100) and fit tag: **Poor / Good / Excellent**.
  - `ScoreBreakdown` Recharts horizontal bar chart for all 5 dimensions.

---

## 5. LLM & Scoring Details

The backend `llm_service.py` uses **Google Gemini 2.5 Flash** with a hybrid approach:

- **Rule-based (no LLM cost)**:
  - Skill matching: exact + synonym-based, deterministic scoring out of 40.
  - Experience depth: formula based on candidate vs. required years (out of 25).
  - Total score recomputed from sub-scores; arithmetic is never trusted from the model.
  - Fit tag derived from total score: `>=75 → Excellent`, `>=50 → Good`, else `Poor`.

- **LLM-based**:
  - Role alignment, project strength, education bonus.
  - Narrative fields: strengths, gaps, suggestions, summary.
  - Strict JSON-only prompts with retries and code-fence stripping.

If Gemini is unavailable, the system falls back to rule-based scores only with a clear summary message.

---

## 6. Typical Workflow

1. Start the backend: `cd backend && python app.py`
2. Start the frontend: `cd frontend && npm run dev`
3. Visit `http://localhost:5173` and log in (use the demo account or sign up).
4. Create a new Job Description (text or PDF).
5. Open the JD detail page and add candidates by uploading their resumes.
6. Click **Evaluate** or **Evaluate All** to see:
   - Fit score (0–100) and fit tag.
   - Score breakdown chart.
   - Matched/missing skills, strengths, gaps, suggestions, and summary.

---

## 7. Notes

- This project is designed for local/dev use with SQLite. For production, point `DATABASE_URL` to a proper DB.
- Make sure your Node version satisfies the Vite requirement; if you see engine warnings, upgrade Node.
- Large PDFs may take a few seconds to process due to text extraction and LLM calls. Use smaller sample resumes while iterating on the UI.

