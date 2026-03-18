"""
llm_service.py  — Multi-Provider Free LLM Service
---------------------------------------------------
Uses a fallback chain of FREE providers:
  1. Groq        — 14,400 req/day, fastest (get key: console.groq.com)
  2. Mistral     — 1 billion tokens/month  (get key: console.mistral.ai)
  3. OpenRouter  — 50 req/day, 30+ free models (get key: openrouter.ai)

All three use the OpenAI-compatible format — one client, swappable backends.

Install:
    pip install openai

.env — add whichever keys you have (at least one required):
    GROQ_API_KEY=gsk_...
    MISTRAL_API_KEY=...
    OPENROUTER_API_KEY=sk-or-...
"""

import json
import logging
import re
import time
import datetime
from typing import Any, Dict, List, Optional, Tuple

from openai import OpenAI, RateLimitError, APIStatusError
from flask import current_app

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Provider registry — all use OpenAI-compatible endpoints
# ─────────────────────────────────────────────────────────────────────────────

PROVIDERS = [
    {
        "name":        "Groq",
        "env_key":     "GROQ_API_KEY",
        "base_url":    "https://api.groq.com/openai/v1",
        "model":       "llama-3.3-70b-versatile",
    },
    {
        "name":        "Mistral",
        "env_key":     "MISTRAL_API_KEY",
        "base_url":    "https://api.mistral.ai/v1",
        "model":       "mistral-small-latest",
    },
    {
        "name":        "OpenRouter",
        "env_key":     "OPENROUTER_API_KEY",
        "base_url":    "https://openrouter.ai/api/v1",
        "model":       "deepseek/deepseek-chat-v3-0324:free",
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# Scoring constants
# ─────────────────────────────────────────────────────────────────────────────

WEIGHTS = {
    "skill_match":      40,
    "experience_depth": 25,
    "role_alignment":   20,
    "project_strength": 10,
    "education_bonus":   5,
}

FIT_TAG_THRESHOLDS = [
    (75, "Excellent"),
    (50, "Good"),
    (0,  "Poor"),
]

SKILL_SYNONYMS: Dict[str, str] = {
    "js": "javascript", "ts": "typescript",
    "node": "node.js", "nodejs": "node.js",
    "react.js": "react", "reactjs": "react",
    "vue.js": "vue", "vuejs": "vue",
    "py": "python", "ml": "machine learning",
    "dl": "deep learning", "nlp": "natural language processing",
    "k8s": "kubernetes", "gcp": "google cloud",
    "aws": "amazon web services", "ci/cd": "cicd",
    "postgres": "postgresql", "mongo": "mongodb",
    "rest api": "rest", "restful": "rest", "restful api": "rest",
    "oop": "object oriented programming",
}

_COMMON_SKILLS = {
    "python", "javascript", "typescript", "java", "c++", "c#", "go", "rust",
    "react", "vue", "angular", "node.js", "django", "flask", "fastapi", "spring",
    "sql", "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
    "aws", "google cloud", "azure", "docker", "kubernetes", "terraform",
    "git", "linux", "rest", "graphql", "machine learning", "deep learning",
    "tensorflow", "pytorch", "scikit-learn", "pandas", "numpy",
    "html", "css", "tailwind", "figma", "agile", "scrum",
}

# ─────────────────────────────────────────────────────────────────────────────
# Provider client — OpenAI-compatible for ALL providers
# ─────────────────────────────────────────────────────────────────────────────

def _get_configured_providers() -> List[Dict]:
    """Return only providers that have an API key set in config."""
    configured = []
    for p in PROVIDERS:
        key = current_app.config.get(p["env_key"])
        if key:
            configured.append({**p, "api_key": key})
    return configured


def _call_llm(system: str, user: str) -> str:
    """
    Try each configured provider in order.
    On 429 RateLimitError, silently move to the next provider.
    Raises the last error if all providers fail.
    """
    providers = _get_configured_providers()
    if not providers:
        raise RuntimeError(
            "No LLM API keys configured. "
            "Add at least one of: GROQ_API_KEY, MISTRAL_API_KEY, OPENROUTER_API_KEY to your .env"
        )

    last_error = None
    for p in providers:
        try:
            logger.info("Calling %s / %s", p["name"], p["model"])
            client = OpenAI(api_key=p["api_key"], base_url=p["base_url"])
            resp = client.chat.completions.create(
                model=p["model"],
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user",   "content": user},
                ],
                temperature=0.0,
                max_tokens=2048,
            )
            text = resp.choices[0].message.content or ""
            logger.info("Success with %s", p["name"])
            return text.strip()

        except (RateLimitError, APIStatusError) as e:
            code = getattr(e, "status_code", None)
            if code == 429 or isinstance(e, RateLimitError):
                logger.warning("%s quota hit — trying next provider.", p["name"])
                last_error = e
                continue
            logger.error("%s API error %s — trying next.", p["name"], code)
            last_error = e
            continue

        except Exception as e:
            logger.warning("%s unexpected error: %s — trying next.", p["name"], str(e)[:100])
            last_error = e
            continue

    # All failed — wait 60s and retry first provider once
    logger.warning("All providers exhausted. Waiting 60s then retrying %s...", providers[0]["name"])
    time.sleep(60)
    client = OpenAI(api_key=providers[0]["api_key"], base_url=providers[0]["base_url"])
    resp = client.chat.completions.create(
        model=providers[0]["model"],
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
        temperature=0.0,
        max_tokens=2048,
    )
    return (resp.choices[0].message.content or "").strip()


# ─────────────────────────────────────────────────────────────────────────────
# JSON parsing
# ─────────────────────────────────────────────────────────────────────────────

def _strip_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
    text = re.sub(r"\n?```$", "", text)
    return text.strip()


def _extract_json_object(text: str) -> Optional[str]:
    s = _strip_fences(text)
    start = s.find("{")
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(s)):
        if s[i] == "{":   depth += 1
        elif s[i] == "}": depth -= 1
        if depth == 0:
            return s[start:i + 1]
    end = s.rfind("}")
    return s[start:end + 1] if end > start else None


def _parse_json(raw: str) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(_strip_fences(raw))
    except json.JSONDecodeError:
        extracted = _extract_json_object(raw)
        if extracted:
            try:
                return json.loads(extracted)
            except json.JSONDecodeError:
                pass
        logger.warning("JSON parse failed. Snippet: %s", raw[:200])
        return None


def _call_with_json_retry(system: str, user: str) -> Optional[Dict[str, Any]]:
    """Call LLM, parse JSON. Retry once with stricter prompt on parse failure."""
    try:
        raw = _call_llm(system, user)
        result = _parse_json(raw)
        if result is not None:
            return result

        logger.info("Parse failed — retrying with stricter instructions.")
        raw2 = _call_llm(
            system,
            "Your previous response was not valid JSON.\n"
            "Output ONLY a raw JSON object. No markdown, no explanation, no trailing text.\n\n"
            + user
        )
        return _parse_json(raw2)

    except Exception:
        logger.exception("LLM call failed completely")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Rule-based helpers  (zero API cost)
# ─────────────────────────────────────────────────────────────────────────────

def _normalise_skill(s: str) -> str:
    return SKILL_SYNONYMS.get(s.strip().lower(), s.strip().lower())


def _normalise_skills(skills: List[str]) -> List[str]:
    seen, out = set(), []
    for s in skills:
        n = _normalise_skill(s)
        if n and n not in seen:
            seen.add(n); out.append(n)
    return out


def _compute_fit_tag(score: float) -> str:
    for threshold, tag in FIT_TAG_THRESHOLDS:
        if score >= threshold:
            return tag
    return "Poor"


def _compute_skill_match(
    candidate_skills: List[str],
    required_skills:  List[str],
    preferred_skills: List[str],
) -> Dict[str, Any]:
    cand  = set(_normalise_skills(candidate_skills))
    req   = _normalise_skills(required_skills)
    pref  = _normalise_skills(preferred_skills)

    matched_req  = [s for s in req  if s in cand]
    missing_req  = [s for s in req  if s not in cand]
    matched_pref = [s for s in pref if s in cand]

    req_r  = len(matched_req)  / len(req)  if req  else 0
    pref_r = len(matched_pref) / len(pref) if pref else 0

    return {
        "skill_match_score": round((req_r * 30) + (pref_r * 10), 1),
        "matched_skills":    matched_req + matched_pref,
        "missing_skills":    missing_req,
    }


def _compute_experience_score(candidate_years: float, min_required: float) -> float:
    if min_required <= 0: return 20.0
    r = candidate_years / min_required
    if r >= 1.5:  return 25.0
    if r >= 1.0:  return round(20.0 + (r - 1.0) * 10,  1)
    if r >= 0.75: return round(15.0 + (r - 0.75) * 20, 1)
    if r >= 0.5:  return round(8.0  + (r - 0.5)  * 28, 1)
    return round(r * 16, 1)


def _clamp_and_tag(s: Dict[str, Any]) -> Dict[str, Any]:
    for key, cap in [
        ("skill_match_score",      WEIGHTS["skill_match"]),
        ("experience_depth_score", WEIGHTS["experience_depth"]),
        ("role_alignment_score",   WEIGHTS["role_alignment"]),
        ("project_strength_score", WEIGHTS["project_strength"]),
        ("education_bonus_score",  WEIGHTS["education_bonus"]),
    ]:
        s[key] = max(0.0, min(float(s.get(key, 0)), cap))

    s["total_score"] = min(round(sum([
        s["skill_match_score"], s["experience_depth_score"],
        s["role_alignment_score"], s["project_strength_score"],
        s["education_bonus_score"],
    ]), 1), 100.0)
    s["fit_tag"] = _compute_fit_tag(s["total_score"])
    return s


def _quick_extract_skills(text: str) -> List[str]:
    lower = text.lower()
    found = [s for s in _COMMON_SKILLS if s in lower]
    tech  = re.findall(r'\b[A-Z][a-zA-Z]+(?:\.[a-zA-Z]+)*\b|\b\w+\+\+\b|\b\w+\.js\b', text)
    return list(set(found + [t.lower() for t in tech[:20]]))


def _quick_extract_jd(jd: str) -> Tuple[List[str], List[str], float]:
    lower = jd.lower()
    min_years = 0.0
    for pat in [
        r'(\d+)\+?\s*(?:to\s*\d+\s*)?years?\s*(?:of\s*)?(?:experience|exp)',
        r'minimum\s+(\d+)\s*years?', r'at\s+least\s+(\d+)\s*years?',
    ]:
        m = re.search(pat, lower)
        if m: min_years = float(m.group(1)); break

    req_sec, pref_sec, cur = "", "", "required"
    for line in jd.split("\n"):
        ll = line.lower()
        if any(w in ll for w in ["preferred","nice to have","bonus","desirable"]): cur = "preferred"
        elif any(w in ll for w in ["required","must have","mandatory"]): cur = "required"
        if cur == "required": req_sec  += " " + line
        else:                 pref_sec += " " + line

    req  = [s for s in _COMMON_SKILLS if s in req_sec.lower()]
    pref = [s for s in _COMMON_SKILLS if s in pref_sec.lower() and s not in req]
    if not req: req = [s for s in _COMMON_SKILLS if s in lower]
    return req, pref, min_years


def _quick_extract_years(text: str) -> float:
    yr = datetime.datetime.now().year
    ranges = re.findall(
        r'(20\d{2}|19\d{2})\s*[-\u2013\u2014to]+\s*(20\d{2}|19\d{2}|present|current|now)',
        text.lower()
    )
    total = 0.0
    for s, e in ranges:
        try:
            start = int(s)
            end   = yr if e in ("present","current","now") else int(e)
            d     = max(0, end - start)
            if 0 < d <= 20: total += d
        except ValueError:
            continue
    if total > 0: return min(total, 40.0)
    count = len(re.findall(
        r'\b(engineer|developer|analyst|manager|lead|intern|consultant|designer)\b',
        text.lower()
    ))
    return min(float(count) * 1.5, 15.0)


# ─────────────────────────────────────────────────────────────────────────────
# Single combined LLM prompt
# ─────────────────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = (
    "You are an expert resume evaluator. "
    "You receive a resume, a job description, and pre-computed rule-based scores. "
    "Fill in ONLY the fields marked YOUR TASK. "
    "Return ONLY raw valid JSON — no markdown, no explanation, no code fences."
)

_USER_TEMPLATE = """Pre-computed scores (copy these EXACTLY into your response):
  skill_match_score      = {skill_match_score}
  experience_depth_score = {experience_depth_score}
  matched_skills         = {matched_skills}
  missing_skills         = {missing_skills}

YOUR TASK — score and analyse:
  role_alignment_score   : number 0–{max_align}  (candidate responsibilities vs JD responsibilities)
  project_strength_score : number 0–{max_proj}   (project relevance, tech overlap, outcomes)
  education_bonus_score  : number 0–{max_edu}    (meets/exceeds education requirement)
  strengths              : list of 2–4 specific strengths for THIS role
  gaps                   : list of 2–4 honest gaps or missing items
  suggestions            : list of exactly 3 concrete improvements
  summary                : 2–3 sentence overall fit assessment
  candidate_name         : string or null
  candidate_email        : string or null
  candidate_phone        : string or null
  total_experience_years : number

Return this JSON structure (fill in the zeroes/nulls/empty arrays):
{{
  "candidate_name":          null,
  "candidate_email":         null,
  "candidate_phone":         null,
  "total_experience_years":  0,
  "skill_match_score":       {skill_match_score},
  "experience_depth_score":  {experience_depth_score},
  "role_alignment_score":    0,
  "project_strength_score":  0,
  "education_bonus_score":   0,
  "matched_skills":          {matched_skills},
  "missing_skills":          {missing_skills},
  "strengths":               [],
  "gaps":                    [],
  "suggestions":             [],
  "summary":                 ""
}}

--- RESUME ---
{resume_text}

--- JOB DESCRIPTION ---
{jd_text}
"""


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def evaluate_candidate(resume_text: str, jd_text: str) -> Optional[Dict[str, Any]]:
    """
    Main entry point — ONE API call per evaluation.

    In your evaluate route:
        result = evaluate_candidate(candidate.resume_text, jd.description)
        if result:
            candidate.fit_score            = result["total_score"]
            candidate.fit_tag              = result["fit_tag"]
            candidate.skill_match_score    = result["skill_match_score"]
            candidate.experience_score     = result["experience_depth_score"]
            candidate.role_alignment_score = result["role_alignment_score"]
            candidate.project_score        = result["project_strength_score"]
            candidate.education_score      = result["education_bonus_score"]
            candidate.matched_skills       = json.dumps(result["matched_skills"])
            candidate.missing_skills       = json.dumps(result["missing_skills"])
            candidate.strengths            = json.dumps(result["strengths"])
            candidate.gaps                 = json.dumps(result["gaps"])
            candidate.suggestions          = json.dumps(result["suggestions"])
            candidate.summary              = result["summary"]
            candidate.is_evaluated         = True
    """
    if not resume_text or len(resume_text.strip()) < 50:
        logger.warning("Resume text too short — skipping")
        return None
    if not jd_text or len(jd_text.strip()) < 30:
        logger.warning("JD text too short — skipping")
        return None

    # Step 1 — Rule-based (free, instant)
    req_skills, pref_skills, min_years = _quick_extract_jd(jd_text)
    skill_result = _compute_skill_match(
        _quick_extract_skills(resume_text), req_skills, pref_skills
    )
    exp_score = _compute_experience_score(
        _quick_extract_years(resume_text), min_years
    )

    # Step 2 — One LLM call across all providers
    prompt = _USER_TEMPLATE.format(
        skill_match_score      = skill_result["skill_match_score"],
        experience_depth_score = round(exp_score, 1),
        matched_skills         = json.dumps(skill_result["matched_skills"]),
        missing_skills         = json.dumps(skill_result["missing_skills"]),
        max_align              = WEIGHTS["role_alignment"],
        max_proj               = WEIGHTS["project_strength"],
        max_edu                = WEIGHTS["education_bonus"],
        resume_text            = resume_text[:3000],
        jd_text                = jd_text[:2000],
    )

    result = _call_with_json_retry(_SYSTEM_PROMPT, prompt)

    if result is None:
        logger.warning("All providers failed — returning rule-based fallback")
        return _fallback_result(skill_result, exp_score)

    # Step 3 — Lock in rule-based scores
    result["skill_match_score"]      = skill_result["skill_match_score"]
    result["experience_depth_score"] = round(exp_score, 1)
    result["matched_skills"]         = skill_result["matched_skills"]
    result["missing_skills"]         = skill_result["missing_skills"]

    # Step 4 — Clamp, recompute total, add fit_tag
    return _clamp_and_tag(result)


def _fallback_result(skill_result: Dict, exp_score: float) -> Dict[str, Any]:
    return _clamp_and_tag({
        "candidate_name": None, "candidate_email": None, "candidate_phone": None,
        "total_experience_years":  0,
        "skill_match_score":       skill_result["skill_match_score"],
        "experience_depth_score":  round(exp_score, 1),
        "role_alignment_score":    0,
        "project_strength_score":  0,
        "education_bonus_score":   0,
        "matched_skills":          skill_result["matched_skills"],
        "missing_skills":          skill_result["missing_skills"],
        "strengths":   ["LLM unavailable — rule-based scores only"],
        "gaps":        ["Re-evaluate when a provider quota resets"],
        "suggestions": [
            "Wait for API quota to reset (usually resets daily)",
            "Add another provider key to .env for automatic fallback",
            "Try evaluating again in a few minutes",
        ],
        "summary": "Partial evaluation using rule-based scoring only. Re-evaluate for full LLM analysis.",
    })


# ─────────────────────────────────────────────────────────────────────────────
# Legacy shims — keeps old route code working without any changes
# ─────────────────────────────────────────────────────────────────────────────

def extract_resume_structure(resume_text: str) -> Optional[Dict[str, Any]]:
    if not resume_text or len(resume_text.strip()) < 50:
        return None
    return {
        "skills": _quick_extract_skills(resume_text),
        "total_experience_years": _quick_extract_years(resume_text),
        "experience": [], "education": [], "projects": [], "extracurriculars": [],
    }


def extract_jd_structure(jd_text: str) -> Optional[Dict[str, Any]]:
    if not jd_text or len(jd_text.strip()) < 30:
        return None
    req, pref, min_yrs = _quick_extract_jd(jd_text)
    return {
        "required_skills": req, "preferred_skills": pref,
        "min_experience_years": min_yrs,
        "responsibilities": [], "domain_keywords": [],
    }


def score_candidate(resume_json: Dict, jd_json: Dict) -> Optional[Dict[str, Any]]:
    """Legacy shim — new code should call evaluate_candidate() directly."""
    sr = _compute_skill_match(
        resume_json.get("skills", []),
        jd_json.get("required_skills", []),
        jd_json.get("preferred_skills", []),
    )
    es = _compute_experience_score(
        float(resume_json.get("total_experience_years") or 0),
        float(jd_json.get("min_experience_years") or 0),
    )
    return _fallback_result(sr, es)