import React from "react";
import FitTag from "./FitTag.jsx";

export default function TopScorerBanner({ candidate }) {
  if (!candidate || !candidate.is_evaluated) return null;

  const topSkills = (candidate.matched_skills || []).slice(0, 3);

  return (
    <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 flex items-center justify-between gap-4">
      <div>
        <p className="text-xs font-semibold text-amber-900 uppercase tracking-wide">
          Top Candidate
        </p>
        <p className="text-sm font-semibold text-slate-900 flex items-center gap-2">
          {candidate.name}
          <FitTag tag={candidate.fit_tag} />
          <span
            className={`text-xs font-semibold ${
              (candidate.fit_score ?? 0) >= 75
                ? "text-emerald-700"
                : (candidate.fit_score ?? 0) >= 50
                ? "text-amber-700"
                : "text-red-700"
            }`}
          >
            {Math.round(candidate.fit_score ?? 0)} / 100
          </span>
        </p>
        {topSkills.length > 0 && (
          <div className="mt-1 flex flex-wrap gap-1">
            {topSkills.map((s) => (
              <span
                key={s}
                className="px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 text-[11px]"
              >
                {s}
              </span>
            ))}
          </div>
        )}
      </div>
      <div className="hidden sm:block text-xs text-amber-900 max-w-xs">
        This candidate currently has the highest overall fit score for this role.
      </div>
    </div>
  );
}

