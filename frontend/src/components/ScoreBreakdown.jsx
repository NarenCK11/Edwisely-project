import React from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  LabelList,
} from "recharts";

const METRICS = [
  { key: "skill_match_score", label: "Skill Match", max: 40, color: "#4f46e5" },
  { key: "experience_score", label: "Experience Depth", max: 25, color: "#0ea5e9" },
  { key: "role_alignment_score", label: "Role Alignment", max: 20, color: "#10b981" },
  { key: "project_score", label: "Project Strength", max: 10, color: "#f59e0b" },
  { key: "education_score", label: "Education Bonus", max: 5, color: "#ec4899" },
];

export default function ScoreBreakdown({ candidate }) {
  if (!candidate) return null;

  const data = METRICS.map((m) => ({
    name: m.label,
    value: candidate[m.key] ?? 0,
    max: m.max,
    color: m.color,
    label: `${candidate[m.key] ?? 0} / ${m.max}`,
  }));

  return (
    <div className="w-full h-64">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ left: 80, right: 20 }}>
          <XAxis type="number" domain={[0, (dataMax) => Math.max(dataMax, 40)]} hide />
          <YAxis
            type="category"
            dataKey="name"
            tick={{ fontSize: 12, fill: "#475569" }}
            width={120}
          />
          <Tooltip
            formatter={(value, _, props) => [`${value} / ${props.payload.max}`, "Score"]}
          />
          <Bar dataKey="value" radius={[0, 4, 4, 0]} isAnimationActive={false}>
            <LabelList
              dataKey="label"
              position="insideRight"
              style={{ fill: "#0f172a", fontSize: 11 }}
            />
            {data.map((entry, index) => (
              <cell key={index} fill={entry.color} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

