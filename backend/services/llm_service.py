"""
llm_service.py
--------------
AI-Powered Resume Evaluator — LLM Service
Uses Google Gemini 2.5 Flash (FREE tier, no credit card needed).

Setup:
    pip install google-generativeai

Get your free API key at: https://aistudio.google.com
Set in .env:  GEMINI_API_KEY=your-key-here
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

import google.generativeai as genai
from flask import current_app

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Score weights  (must sum to 100)
# ─────────────────────────────────────────────────────────────────────────────
WEIGHTS = {
    "skill_match":        40,
    "experience_depth":   25,
    "role_alignment":     20,
    "project_strength":   10,
    "education_bonus":     5,
}

# Tag thresholds
FIT_TAG_THRESHOLDS = [
    (75, "Excellent"),
    (50, "Good"),
    (0,  "Poor"),
]

# Section header keywords used by the rule-based resume parser
SECTION_KEYWORDS = {
    "skills":          ["skill", "technologies", "tech stack", "competencies", "tools", "languages"],
    "experience":      ["experience", "employment", "work history", "career", "positions held"],
    "education":       ["education", "academic", "qualification", "degree", "university", "college"],
    "projects":        ["project", "portfolio", "built", "developed", "created"],
    "extracurriculars":["extracurricular", "volunteer", "activities", "leadership", "clubs", "awards", "certifications"],
}

# Common skill synonyms — rule-based normalisation
SKILL_SYNONYMS: Dict[str, str] = {
    "js": "javascript",
    "ts": "typescript",
    "node": "node.js",
    "nodejs": "node.js",
    "react.js": "react",
    "reactjs": "react",
    "vue.js": "vue",
    "vuejs": "vue",
    "py": "python",
    "ml": "machine learning",
    "dl": "deep learning",
    "nlp": "natural language processing",
    "k8s": "kubernetes",
    "gcp": "google cloud",
    "aws": "amazon web services",
    "ci/cd": "cicd",
    "postgres": "postgresql",
    "mongo": "mongodb",
    "rest api": "rest",
    "restful": "rest",
    "restful api": "rest",
    "oop": "object oriented programming",
}


# ─────────────────────────────────────────────────────────────────────────────
# Gemini client helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_model() -> genai.GenerativeModel:
    api_key = current_app.config.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured in your .env / Flask config")
    genai.configure(api_key=api_key)
    model_name = current_app.config.get("GEMINI_MODEL", "gemini-2.5-flash")
    return genai.GenerativeModel(model_name)


def _call_gemini(prompt: str, system_instruction: str = "") -> str:
    """
    Send a prompt to Gemini and return the text response.
    All prompts end with an explicit 'JSON only' reminder to reduce hallucinations.
    """
    model = _get_model()
    full_prompt = (
        f"{system_instruction}\n\n{prompt}\n\n"
        "IMPORTANT: Respond with ONLY raw valid JSON. "
        "No markdown, no code fences, no explanation, no trailing text."
    )
    generation_config = genai.types.GenerationConfig(
        temperature=0.0,
        max_output_tokens=2048,
    )
    response = model.generate_content(
        full_prompt,
        generation_config=generation_config,
    )
    return (response.text or "").strip()


def _strip_fences(text: str) -> str:
    """Remove ```json ... ``` or ``` ... ``` wrappers if Gemini adds them anyway."""
    text = text.strip()
    text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
    text = re.sub(r"\n?```$", "", text)
    return text.strip()


def _parse_json(raw: str) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(_strip_fences(raw))
    except json.JSONDecodeError:
        logger.warning("JSON parse failed. Raw response: %s", raw[:300])
        return None


def _call_gemini_with_retry(prompt: str, system_instruction: str = "") -> Optional[Dict[str, Any]]:
    """Call Gemini, parse JSON. If it fails, retry once with a stricter prompt."""
    try:
        raw = _call_gemini(prompt, system_instruction)
        parsed = _parse_json(raw)
        if parsed is not None:
            return parsed

        logger.info("First parse failed — retrying with stricter prompt.")
        retry_prompt = (
            "Your last response was NOT valid JSON. "
            "This time output ONLY a raw JSON object. "
            "No explanation, no code fences, no comments, no trailing commas.\n\n"
            + prompt
        )
        raw_retry = _call_gemini(retry_prompt, system_instruction)
        return _parse_json(raw_retry)
    except Exception:
        logger.exception("Gemini API call failed")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Rule-based text processing helpers
# ─────────────────────────────────────────────────────────────────────────────

def _normalise_skill(skill: str) -> str:
    """Lowercase + apply synonym map."""
    cleaned = skill.strip().lower()
    return SKILL_SYNONYMS.get(cleaned, cleaned)


def _normalise_skills(skills: List[str]) -> List[str]:
    seen, result = set(), []
    for s in skills:
        norm = _normalise_skill(s)
        if norm and norm not in seen:
            seen.add(norm)
            result.append(norm)
    return result


def _compute_fit_tag(score: float) -> str:
    for threshold, tag in FIT_TAG_THRESHOLDS:
        if score >= threshold:
            return tag
    return "Poor"


def _validate_and_clamp_scores(scoring: Dict[str, Any]) -> Dict[str, Any]:
    """
    Rule-based post-processing on LLM score output:
    1. Clamp every sub-score to its allowed max.
    2. Recompute total_score from sub-scores (never trust LLM arithmetic).
    3. Add fit_tag.
    """
    scoring["skill_match_score"]      = max(0.0, min(float(scoring.get("skill_match_score",      0)), WEIGHTS["skill_match"]))
    scoring["experience_depth_score"] = max(0.0, min(float(scoring.get("experience_depth_score", 0)), WEIGHTS["experience_depth"]))
    scoring["role_alignment_score"]   = max(0.0, min(float(scoring.get("role_alignment_score",   0)), WEIGHTS["role_alignment"]))
    scoring["project_strength_score"] = max(0.0, min(float(scoring.get("project_strength_score", 0)), WEIGHTS["project_strength"]))
    scoring["education_bonus_score"]  = max(0.0, min(float(scoring.get("education_bonus_score",  0)), WEIGHTS["education_bonus"]))

    total = round(
        scoring["skill_match_score"]
        + scoring["experience_depth_score"]
        + scoring["role_alignment_score"]
        + scoring["project_strength_score"]
        + scoring["education_bonus_score"],
        1,
    )
    scoring["total_score"] = min(total, 100.0)
    scoring["fit_tag"]     = _compute_fit_tag(scoring["total_score"])
    return scoring


def _compute_skill_match_rule(
    candidate_skills: List[str],
    required_skills: List[str],
    preferred_skills: List[str],
) -> Dict[str, Any]:
    """
    Pure rule-based skill match (no LLM needed).
    Returns matched, missing lists and raw skill_match_score.
    """
    cand_norm      = set(_normalise_skills(candidate_skills))
    required_norm  = _normalise_skills(required_skills)
    preferred_norm = _normalise_skills(preferred_skills)

    matched_required  = [s for s in required_norm  if s in cand_norm]
    missing_required  = [s for s in required_norm  if s not in cand_norm]
    matched_preferred = [s for s in preferred_norm if s in cand_norm]

    req_ratio  = (len(matched_required)  / len(required_norm))  if required_norm  else 0
    pref_ratio = (len(matched_preferred) / len(preferred_norm)) if preferred_norm else 0

    skill_score = round((req_ratio * 30) + (pref_ratio * 10), 1)

    return {
        "skill_match_score": skill_score,
        "matched_skills":    matched_required + matched_preferred,
        "missing_skills":    missing_required,
    }


def _compute_experience_rule(
    candidate_years: float,
    min_required_years: float,
) -> float:
    """
    Rule-based experience sub-score out of 25.
    Full score if meets requirement, scaled down if below, small bonus if well above.
    """
    if min_required_years <= 0:
        return 20.0

    ratio = candidate_years / min_required_years
    if ratio >= 1.5:
        return 25.0
    elif ratio >= 1.0:
        return 20.0 + (ratio - 1.0) * 10
    elif ratio >= 0.75:
        return 15.0 + (ratio - 0.75) * 20
    elif ratio >= 0.5:
        return 8.0  + (ratio - 0.5)  * 28
    else:
        return round(ratio * 16, 1)


# ─────────────────────────────────────────────────────────────────────────────
# Public functions
# ─────────────────────────────────────────────────────────────────────────────

def extract_resume_structure(resume_text: str) -> Optional[Dict[str, Any]]:
    """
    Extract structured data from resume text.
    Strategy: LLM handles free-form parsing, rules handle normalisation.
    """
    if not resume_text or len(resume_text.strip()) < 50:
        logger.warning("Resume text too short — skipping LLM extraction")
        return None

    system_instruction = (
        "You are an expert resume parser. "
        "Extract every piece of information from the resume into the JSON schema provided. "
        "Be thorough: include all skills, jobs, projects, and education entries. "
        "If a field is not found, use null or an empty array. "
        "Do not invent information."
    )
    schema = """{
  "name":                    "string or null",
  "email":                   "string or null",
  "phone":                   "string or null",
  "skills":                  ["list of ALL technical and soft skills mentioned"],
  "total_experience_years":  "number (estimate total years of work experience)",
  "experience": [
    {
      "company":         "string",
      "role":            "string",
      "duration_years":  "number",
      "highlights":      ["list of key achievements or responsibilities"]
    }
  ],
  "education": [
    {
      "degree":      "string",
      "institution": "string",
      "year":        "string or null"
    }
  ],
  "projects": [
    {
      "name":        "string",
      "tech_stack":  ["list of technologies used"],
      "description": "string"
    }
  ],
  "extracurriculars": ["list of activities, certifications, awards, volunteering"]
}"""

    prompt = (
        f"Parse the resume below into this exact JSON schema.\n"
        f"Schema:\n{schema}\n\n"
        f"Resume Text:\n{resume_text}"
    )

    parsed = _call_gemini_with_retry(prompt, system_instruction)
    if parsed is None:
        return None

    if isinstance(parsed.get("skills"), list):
        parsed["skills"] = _normalise_skills(parsed["skills"])
    if isinstance(parsed.get("total_experience_years"), str):
        try:
            parsed["total_experience_years"] = float(parsed["total_experience_years"])
        except ValueError:
            parsed["total_experience_years"] = 0.0

    return parsed


def extract_jd_structure(jd_text: str) -> Optional[Dict[str, Any]]:
    """
    Extract structured requirements from a job description.
    Strategy: LLM handles parsing, rules normalise skills.
    """
    if not jd_text or len(jd_text.strip()) < 30:
        logger.warning("JD text too short — skipping extraction")
        return None

    system_instruction = (
        "You are an expert at parsing job descriptions for HR and recruiting software. "
        "Extract every requirement, skill, and expectation into the JSON schema provided. "
        "Separate must-have (required) skills from nice-to-have (preferred) skills carefully. "
        "Do not invent requirements not present in the text."
    )
    schema = """{
  "role_title":             "string",
  "required_skills":        ["must-have skills listed explicitly"],
  "preferred_skills":       ["nice-to-have or preferred skills"],
  "min_experience_years":   "number (use 0 if not stated)",
  "responsibilities":       ["list of key job responsibilities"],
  "education_requirements": "string or null",
  "domain_keywords":        ["important domain or industry terms from the JD"]
}"""

    prompt = (
        f"Parse the job description below into this exact JSON schema.\n"
        f"Schema:\n{schema}\n\n"
        f"Job Description Text:\n{jd_text}"
    )

    parsed = _call_gemini_with_retry(prompt, system_instruction)
    if parsed is None:
        return None

    if isinstance(parsed.get("required_skills"), list):
        parsed["required_skills"] = _normalise_skills(parsed["required_skills"])
    if isinstance(parsed.get("preferred_skills"), list):
        parsed["preferred_skills"] = _normalise_skills(parsed["preferred_skills"])
    if isinstance(parsed.get("min_experience_years"), str):
        try:
            parsed["min_experience_years"] = float(parsed["min_experience_years"])
        except ValueError:
            parsed["min_experience_years"] = 0.0

    return parsed


def score_candidate(
    resume_json: Dict[str, Any],
    jd_json: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """
    Score a candidate against a JD using a HYBRID approach:
    - skill_match_score    → 100% rule-based (exact + synonym matching)
    - experience_score     → 100% rule-based (years ratio formula)
    - role_alignment_score → LLM (requires semantic understanding)
    - project_strength     → LLM (requires qualitative judgement)
    - education_bonus      → LLM (varies by field and role context)
    - strengths/gaps/suggestions/summary → LLM
    """

    # ── Step 1: Rule-based scores (no LLM cost) ──────────────────────────────
    skill_result = _compute_skill_match_rule(
        candidate_skills  = resume_json.get("skills", []),
        required_skills   = jd_json.get("required_skills", []),
        preferred_skills  = jd_json.get("preferred_skills", []),
    )

    experience_score = _compute_experience_rule(
        candidate_years    = float(resume_json.get("total_experience_years") or 0),
        min_required_years = float(jd_json.get("min_experience_years") or 0),
    )

    # ── Step 2: LLM-only scores (semantic/qualitative dimensions) ─────────────
    system_instruction = (
        "You are a senior technical recruiter scoring a candidate against a job description.\n"
        "You will be given pre-computed scores for skill_match and experience_depth — "
        "DO NOT change those fields, just include them as-is.\n"
        "Score the remaining three dimensions honestly and return the JSON schema below.\n\n"
        "Scoring rules:\n"
        f"- role_alignment_score: 0–{WEIGHTS['role_alignment']} pts. "
        "How closely do the candidate's past responsibilities and domain keywords match the JD responsibilities?\n"
        f"- project_strength_score: 0–{WEIGHTS['project_strength']} pts. "
        "Are the candidate's projects relevant? Do they show measurable outcomes or tech stack overlap with JD?\n"
        f"- education_bonus_score: 0–{WEIGHTS['education_bonus']} pts. "
        "Does the candidate meet or exceed the stated education requirement?\n"
        "- strengths: 2–4 specific positive points about this candidate for this role.\n"
        "- gaps: 2–4 honest weaknesses or missing items.\n"
        "- suggestions: 3 concrete improvements the candidate could make to strengthen their profile.\n"
        "- summary: 2–3 sentences: overall fit assessment.\n"
        "Be specific and evidence-based. No generic praise."
    )

    schema = f"""{{
  "role_alignment_score":     "number 0–{WEIGHTS['role_alignment']}",
  "project_strength_score":   "number 0–{WEIGHTS['project_strength']}",
  "education_bonus_score":    "number 0–{WEIGHTS['education_bonus']}",
  "strengths":                ["string", "string", ...],
  "gaps":                     ["string", "string", ...],
  "suggestions":              ["string", "string", "string"],
  "summary":                  "string"
}}"""

    prompt = (
        f"Pre-computed (do not change):\n"
        f"  skill_match_score = {skill_result['skill_match_score']}\n"
        f"  experience_depth_score = {round(experience_score, 1)}\n\n"
        f"Matched skills (for context): {skill_result['matched_skills']}\n"
        f"Missing skills (for context): {skill_result['missing_skills']}\n\n"
        f"Output schema:\n{schema}\n\n"
        f"Candidate Resume JSON:\n{json.dumps(resume_json, ensure_ascii=False)}\n\n"
        f"Job Description JSON:\n{json.dumps(jd_json, ensure_ascii=False)}"
    )

    llm_result = _call_gemini_with_retry(prompt, system_instruction)

    if llm_result is None:
        logger.warning("LLM scoring failed — falling back to rule-based scores only")
        llm_result = {
            "role_alignment_score":   0,
            "project_strength_score": 0,
            "education_bonus_score":  0,
            "strengths":   ["Could not be evaluated — LLM service unavailable"],
            "gaps":        ["Could not be evaluated — LLM service unavailable"],
            "suggestions": ["Re-run evaluation when the LLM service is available"],
            "summary":     "Automatic evaluation failed. Partial rule-based scores are shown.",
        }

    # ── Step 3: Merge rule-based + LLM scores ─────────────────────────────────
    merged = {
        "skill_match_score":      skill_result["skill_match_score"],
        "experience_depth_score": round(experience_score, 1),
        "role_alignment_score":   llm_result.get("role_alignment_score", 0),
        "project_strength_score": llm_result.get("project_strength_score", 0),
        "education_bonus_score":  llm_result.get("education_bonus_score", 0),
        "matched_skills":         skill_result["matched_skills"],
        "missing_skills":         skill_result["missing_skills"],
        "strengths":              llm_result.get("strengths", []),
        "gaps":                   llm_result.get("gaps", []),
        "suggestions":            llm_result.get("suggestions", []),
        "summary":                llm_result.get("summary", ""),
    }

    # ── Step 4: Rule-based validation, clamping, and fit_tag ─────────────────
    return _validate_and_clamp_scores(merged)

