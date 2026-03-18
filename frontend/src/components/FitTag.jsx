import React from "react";

const FIT_THRESHOLDS = {
  Excellent: { min: 75, color: "#065f46", bg: "#d1fae5" },
  Good: { min: 50, color: "#92400e", bg: "#fef3c7" },
  Poor: { min: 0, color: "#991b1b", bg: "#fee2e2" },
};

export default function FitTag({ score, tag }) {
  let label = tag;
  if (!label && typeof score === "number") {
    if (score >= FIT_THRESHOLDS.Excellent.min) label = "Excellent";
    else if (score >= FIT_THRESHOLDS.Good.min) label = "Good";
    else label = "Poor";
  }
  if (!label) return null;
  const cfg = FIT_THRESHOLDS[label] || FIT_THRESHOLDS.Poor;

  return (
    <span
      className="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium"
      style={{ backgroundColor: cfg.bg, color: cfg.color }}
    >
      {label}
    </span>
  );
}

