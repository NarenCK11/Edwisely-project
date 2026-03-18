import React from "react";
import FitTag from "./FitTag.jsx";

export default function JDCard({ jd, onClick, onDelete }) {
  const top = jd.top_candidate;

  return (
    <div
      className="relative bg-white border border-slate-200 rounded-lg p-4 shadow-sm hover:border-indigo-500 cursor-pointer transition-colors"
      onClick={onClick}
    >
      <div className="flex justify-between items-start gap-2 mb-2">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">{jd.role_name}</h3>
          <p className="text-xs text-slate-600">{jd.company}</p>
        </div>
        {onDelete && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onDelete();
            }}
            className="text-xs text-red-600 hover:text-red-700"
          >
            Delete
          </button>
        )}
      </div>
      <p className="text-[11px] text-slate-500 mb-2">
        Created{" "}
        {jd.created_at ? new Date(jd.created_at).toLocaleDateString() : "—"}
      </p>
      <div className="flex items-center justify-between text-xs text-slate-700">
        <span>{jd.total_candidates ?? 0} candidates</span>
        {top ? (
          <div className="flex items-center gap-2">
            <span className="font-medium">{top.name}</span>
            <FitTag score={top.fit_score} />
            <span className="text-[11px] text-slate-500">
              {Math.round(top.fit_score)} / 100
            </span>
          </div>
        ) : (
          <span className="text-[11px] text-slate-500">
            No candidates yet
          </span>
        )}
      </div>
    </div>
  );
}

