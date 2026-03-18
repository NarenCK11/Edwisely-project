import React, { useState } from "react";
import FitTag from "./FitTag.jsx";
import ScoreBreakdown from "./ScoreBreakdown.jsx";

export default function CandidateCard({
  candidate,
  rank,
  onEvaluate,
  onReevaluate,
  onDelete,
  loadingEvaluate = false,
}) {
  const [expanded, setExpanded] = useState(false);

  const score = candidate.fit_score ?? 0;
  const scoreColor =
    score >= 75 ? "text-emerald-700" : score >= 50 ? "text-amber-700" : "text-red-700";

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <span className="text-xs font-semibold text-slate-500">{rank}.</span>
          <div>
            <div className="flex items-center gap-2">
              <p className="text-sm font-semibold text-slate-900">{candidate.name}</p>
              <FitTag score={candidate.fit_score} tag={candidate.fit_tag} />
            </div>
            <p className="text-xs text-slate-600">
              {candidate.email || "No email"}{" "}
              {candidate.phone ? `• ${candidate.phone}` : ""}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {candidate.is_evaluated ? (
            <div className="text-right">
              <p className={`text-base font-semibold ${scoreColor}`}>
                {Math.round(score)} / 100
              </p>
              <div className="mt-1 h-1.5 w-24 rounded-full bg-slate-100 overflow-hidden">
                <div
                  className={`h-full ${
                    score >= 75
                      ? "bg-emerald-500"
                      : score >= 50
                      ? "bg-amber-400"
                      : "bg-red-400"
                  }`}
                  style={{ width: `${Math.min(score, 100)}%` }}
                />
              </div>
            </div>
          ) : (
            <span className="text-[11px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-700">
              Pending evaluation
            </span>
          )}
        </div>
      </div>
      <div className="mt-3 flex flex-wrap gap-2 justify-between items-center">
        <div className="flex gap-2 text-xs">
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            className="text-indigo-600 hover:text-indigo-700"
          >
            {expanded ? "Hide details" : "View details"}
          </button>
          {candidate.is_evaluated ? (
            <button
              type="button"
              onClick={onReevaluate}
              disabled={loadingEvaluate}
              className="text-xs text-slate-600 hover:text-slate-800"
            >
              {loadingEvaluate ? "Re-evaluating..." : "Re-evaluate"}
            </button>
          ) : (
            <button
              type="button"
              onClick={onEvaluate}
              disabled={loadingEvaluate}
              className="text-xs text-indigo-600 hover:text-indigo-700"
            >
              {loadingEvaluate ? "Evaluating..." : "Evaluate"}
            </button>
          )}
        </div>
        <button
          type="button"
          onClick={onDelete}
          className="text-xs text-red-600 hover:text-red-700"
        >
          Delete
        </button>
      </div>
      {expanded && candidate.is_evaluated && (
        <div className="mt-4 border-t border-slate-200 pt-3 text-xs text-slate-700 space-y-3">
          <ScoreBreakdown candidate={candidate} />
          {candidate.summary && (
            <p className="text-sm text-slate-800">
              <span className="font-semibold">Summary: </span>
              {candidate.summary}
            </p>
          )}
          {Array.isArray(candidate.matched_skills) &&
            candidate.matched_skills.length > 0 && (
              <div>
                <p className="font-semibold mb-1 text-xs text-slate-800">
                  Matched Skills
                </p>
                <div className="flex flex-wrap gap-1">
                  {candidate.matched_skills.map((s) => (
                    <span
                      key={s}
                      className="px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 text-[11px]"
                    >
                      {s}
                    </span>
                  ))}
                </div>
              </div>
            )}
          {Array.isArray(candidate.missing_skills) &&
            candidate.missing_skills.length > 0 && (
              <div>
                <p className="font-semibold mb-1 text-xs text-slate-800">
                  Missing Skills
                </p>
                <div className="flex flex-wrap gap-1">
                  {candidate.missing_skills.map((s) => (
                    <span
                      key={s}
                      className="px-2 py-0.5 rounded-full bg-red-100 text-red-800 text-[11px]"
                    >
                      {s}
                    </span>
                  ))}
                </div>
              </div>
            )}
          {Array.isArray(candidate.strengths) && candidate.strengths.length > 0 && (
            <div>
              <p className="font-semibold mb-1 text-xs text-slate-800">Strengths</p>
              <ul className="list-disc pl-4 space-y-1">
                {candidate.strengths.map((s, idx) => (
                  <li key={idx}>{s}</li>
                ))}
              </ul>
            </div>
          )}
          {Array.isArray(candidate.gaps) && candidate.gaps.length > 0 && (
            <div>
              <p className="font-semibold mb-1 text-xs text-slate-800">Gaps</p>
              <ul className="list-disc pl-4 space-y-1">
                {candidate.gaps.map((s, idx) => (
                  <li key={idx}>{s}</li>
                ))}
              </ul>
            </div>
          )}
          {Array.isArray(candidate.suggestions) &&
            candidate.suggestions.length > 0 && (
              <div>
                <p className="font-semibold mb-1 text-xs text-slate-800">
                  Suggestions
                </p>
                <ul className="list-disc pl-4 space-y-1">
                  {candidate.suggestions.map((s, idx) => (
                    <li key={idx}>{s}</li>
                  ))}
                </ul>
              </div>
            )}
        </div>
      )}
    </div>
  );
}

