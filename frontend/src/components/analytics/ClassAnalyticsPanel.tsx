"use client";

// Staff analytics: pick a section -> class KPIs + risk distribution + at-risk table.
import { useState } from "react";

import { ApiError } from "@/lib/api";
import {
  BAND_BAR,
  BAND_STYLES,
  ClassAnalytics,
  RiskBand,
  StudentRisk,
  fmt,
  sectionAnalytics,
  sectionAtRisk,
} from "./analyticsApi";
import SectionPicker from "./SectionPicker";

const BANDS: RiskBand[] = ["high", "medium", "low"];

export default function ClassAnalyticsPanel() {
  const [sectionId, setSectionId] = useState<number | null>(null);
  const [summary, setSummary] = useState<ClassAnalytics | null>(null);
  const [rows, setRows] = useState<StudentRisk[]>([]);
  const [bandFilter, setBandFilter] = useState<RiskBand | "">("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load(section: number | null, band: RiskBand | "") {
    setError(null);
    if (section == null) {
      setSummary(null);
      setRows([]);
      return;
    }
    setLoading(true);
    try {
      const [s, r] = await Promise.all([
        sectionAnalytics(section),
        sectionAtRisk(section, band || null),
      ]);
      setSummary(s);
      setRows(r);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to load analytics");
    } finally {
      setLoading(false);
    }
  }

  function onSection(id: number | null) {
    setSectionId(id);
    setBandFilter("");
    load(id, "");
  }

  function onBand(band: RiskBand | "") {
    setBandFilter(band);
    load(sectionId, band);
  }

  return (
    <div className="space-y-6">
      <div>
        <p className="mb-2 text-sm font-medium text-gray-700 dark:text-slate-300">Pick a section</p>
        <SectionPicker onSection={onSection} />
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}
      {loading && <p className="text-sm text-gray-500 dark:text-slate-400">Loading...</p>}

      {sectionId == null && !loading && (
        <p className="text-sm text-gray-500 dark:text-slate-400">
          Select a section to see its class health and at-risk students.
        </p>
      )}

      {summary && (
        <>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            <Kpi label="Students" value={String(summary.student_count)} />
            <Kpi
              label="Avg attendance"
              value={fmt(summary.avg_attendance_pct, "%")}
            />
            <Kpi label="Avg CGPA" value={fmt(summary.avg_cgpa)} />
            <Kpi
              label="Avg submissions"
              value={fmt(summary.avg_submission_rate, "%")}
            />
            <Kpi
              label="Assignments"
              value={String(summary.total_assignments)}
            />
            <Kpi
              label="Needs attention"
              value={String(summary.at_risk_count)}
              accent={summary.at_risk_count > 0}
            />
          </div>

          <RiskDistribution summary={summary} />

          <div>
            <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-slate-100">
                Students {bandFilter ? `(${bandFilter} risk)` : "by risk"}
              </h2>
              <select
                value={bandFilter}
                onChange={(e) => onBand(e.target.value as RiskBand | "")}
                className="rounded border border-gray-300 dark:border-white/15 px-2 py-1 text-sm"
              >
                <option value="">All bands</option>
                {BANDS.map((b) => (
                  <option key={b} value={b}>
                    {b[0].toUpperCase() + b.slice(1)} risk
                  </option>
                ))}
              </select>
            </div>
            <RiskTable rows={rows} />
          </div>
        </>
      )}
    </div>
  );
}

function Kpi({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent?: boolean;
}) {
  return (
    <div
      className={`rounded-lg border p-3 ${
        accent ? "border-red-200 bg-red-50" : "border-gray-200 dark:border-white/10 bg-white dark:bg-slate-900"
      }`}
    >
      <p className="text-xs text-gray-500 dark:text-slate-400">{label}</p>
      <p className="text-xl font-bold text-gray-900 dark:text-slate-100">{value}</p>
    </div>
  );
}

function RiskDistribution({ summary }: { summary: ClassAnalytics }) {
  const total = summary.student_count || 1;
  const segs: { band: RiskBand; count: number }[] = [
    { band: "high", count: summary.risk_high },
    { band: "medium", count: summary.risk_medium },
    { band: "low", count: summary.risk_low },
  ];
  return (
    <div>
      <p className="mb-2 text-sm font-medium text-gray-700 dark:text-slate-300">
        Risk distribution
      </p>
      <div className="flex h-4 w-full overflow-hidden rounded-full bg-gray-100 dark:bg-slate-800">
        {segs.map((s) =>
          s.count > 0 ? (
            <div
              key={s.band}
              className={BAND_BAR[s.band]}
              style={{ width: `${(s.count / total) * 100}%` }}
              title={`${s.band}: ${s.count}`}
            />
          ) : null,
        )}
      </div>
      <div className="mt-2 flex gap-4 text-xs text-gray-600 dark:text-slate-300">
        {segs.map((s) => (
          <span key={s.band} className="flex items-center gap-1">
            <span
              className={`inline-block h-2 w-2 rounded-full ${BAND_BAR[s.band]}`}
            />
            {s.band[0].toUpperCase() + s.band.slice(1)}: {s.count}
          </span>
        ))}
      </div>
    </div>
  );
}

function RiskTable({ rows }: { rows: StudentRisk[] }) {
  if (rows.length === 0) {
    return <p className="text-sm text-gray-500 dark:text-slate-400">No students to show.</p>;
  }
  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200 dark:border-white/10">
      <table className="min-w-full divide-y divide-gray-200 dark:divide-white/10 text-sm">
        <thead className="bg-gray-50 dark:bg-slate-950 text-left text-xs uppercase text-gray-500 dark:text-slate-400">
          <tr>
            <th className="px-3 py-2">Student</th>
            <th className="px-3 py-2">Risk</th>
            <th className="px-3 py-2">Band</th>
            <th className="px-3 py-2">Attendance</th>
            <th className="px-3 py-2">CGPA</th>
            <th className="px-3 py-2">Submissions</th>
            <th className="px-3 py-2">Reasons</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 dark:divide-white/10">
          {rows.map((r) => (
            <tr key={r.student_id}>
              <td className="px-3 py-2 font-medium text-gray-900 dark:text-slate-100">
                {r.student_name ?? `#${r.student_id}`}
              </td>
              <td className="px-3 py-2 font-semibold">{r.risk_score}</td>
              <td className="px-3 py-2">
                <span
                  className={`rounded px-2 py-0.5 text-xs font-medium ${BAND_STYLES[r.band]}`}
                >
                  {r.band}
                </span>
              </td>
              <td className="px-3 py-2">{fmt(r.attendance_pct, "%")}</td>
              <td className="px-3 py-2">{fmt(r.cgpa)}</td>
              <td className="px-3 py-2">{fmt(r.submission_rate, "%")}</td>
              <td className="px-3 py-2 text-gray-600 dark:text-slate-300">
                {r.reasons.length ? (
                  <div className="flex flex-wrap gap-1">
                    {r.reasons.map((reason, i) => (
                      <span
                        key={i}
                        className="rounded bg-gray-100 dark:bg-slate-800 px-1.5 py-0.5 text-xs"
                      >
                        {reason}
                      </span>
                    ))}
                  </div>
                ) : (
                  <span className="text-gray-400 dark:text-slate-500">No flags</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
