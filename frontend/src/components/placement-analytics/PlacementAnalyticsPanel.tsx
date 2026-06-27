"use client";

// TPO/admin placement dashboard: KPIs + application funnel + per-drive table
// + company leaderboard. Read-only over /placement/analytics/overview.
import { useEffect, useState } from "react";

import { ApiError } from "@/lib/api";
import {
  CompanyStat,
  DrivePerformance,
  FUNNEL_STEPS,
  PlacementAnalytics,
  fmt,
  fmtLpa,
  getOverview,
} from "./placementAnalyticsApi";

export default function PlacementAnalyticsPanel() {
  const [data, setData] = useState<PlacementAnalytics | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getOverview()
      .then(setData)
      .catch((e) =>
        setError(
          e instanceof ApiError ? e.message : "Failed to load analytics",
        ),
      );
  }, []);

  if (error) return <p className="text-sm text-red-600">{error}</p>;
  if (!data) return <p className="text-sm text-gray-500">Loading...</p>;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        <Kpi
          label="Drives"
          value={`${data.total_drives}`}
          sub={`${data.open_drives} open`}
        />
        <Kpi
          label="Applications"
          value={`${data.total_applications}`}
          sub={`${data.unique_applicants} applicants`}
        />
        <Kpi
          label="Placed"
          value={`${data.placed_students}`}
          sub={`of ${data.total_active_students} students`}
          accent={data.placed_students > 0}
        />
        <Kpi label="Placement rate" value={fmt(data.placement_rate, "%")} />
        <Kpi label="Avg package" value={fmtLpa(data.avg_package)} />
        <Kpi
          label="Top package"
          value={fmtLpa(data.highest_package)}
          sub={data.highest_package_company ?? undefined}
        />
      </div>

      <Funnel data={data} />
      <DriveTable rows={data.drives} />
      <CompanyTable rows={data.companies} />
    </div>
  );
}

function Kpi({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: string;
  sub?: string;
  accent?: boolean;
}) {
  return (
    <div
      className={`rounded-lg border p-3 ${
        accent ? "border-green-200 bg-green-50" : "border-gray-200 bg-white"
      }`}
    >
      <p className="text-xs text-gray-500">{label}</p>
      <p className="text-xl font-bold text-gray-900">{value}</p>
      {sub && <p className="mt-0.5 text-xs text-gray-400">{sub}</p>}
    </div>
  );
}

function Funnel({ data }: { data: PlacementAnalytics }) {
  const counts = data.funnel;
  const total =
    counts.applied + counts.shortlisted + counts.selected + counts.rejected ||
    1;
  return (
    <div>
      <p className="mb-2 text-sm font-medium text-gray-700">
        Application funnel
      </p>
      <div className="flex h-4 w-full overflow-hidden rounded-full bg-gray-100">
        {FUNNEL_STEPS.map((s) => {
          const n = counts[s.key];
          return n > 0 ? (
            <div
              key={s.key}
              className={s.bar}
              style={{ width: `${(n / total) * 100}%` }}
              title={`${s.label}: ${n}`}
            />
          ) : null;
        })}
      </div>
      <div className="mt-2 flex flex-wrap gap-2">
        {FUNNEL_STEPS.map((s) => (
          <span
            key={s.key}
            className={`rounded px-2 py-0.5 text-xs font-medium ${s.chip}`}
          >
            {s.label}: {counts[s.key]}
          </span>
        ))}
      </div>
    </div>
  );
}

function DriveTable({ rows }: { rows: DrivePerformance[] }) {
  return (
    <div>
      <h2 className="mb-2 text-lg font-semibold text-gray-900">
        Drive performance
      </h2>
      {rows.length === 0 ? (
        <p className="text-sm text-gray-500">No drives posted yet.</p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50 text-left text-xs uppercase text-gray-500">
              <tr>
                <th className="px-3 py-2">Company</th>
                <th className="px-3 py-2">Role</th>
                <th className="px-3 py-2">Package</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2">Applicants</th>
                <th className="px-3 py-2">Shortlisted</th>
                <th className="px-3 py-2">Selected</th>
                <th className="px-3 py-2">Sel. rate</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {rows.map((r) => (
                <tr key={r.drive_id}>
                  <td className="px-3 py-2 font-medium text-gray-900">
                    {r.company_name}
                  </td>
                  <td className="px-3 py-2 text-gray-600">{r.role_title}</td>
                  <td className="px-3 py-2">{fmtLpa(r.package_lpa)}</td>
                  <td className="px-3 py-2">
                    <span
                      className={`rounded px-2 py-0.5 text-xs font-medium ${
                        r.is_open
                          ? "bg-green-100 text-green-800"
                          : "bg-gray-100 text-gray-600"
                      }`}
                    >
                      {r.is_open ? "open" : "closed"}
                    </span>
                  </td>
                  <td className="px-3 py-2">{r.applicants}</td>
                  <td className="px-3 py-2">{r.shortlisted}</td>
                  <td className="px-3 py-2 font-semibold">{r.selected}</td>
                  <td className="px-3 py-2">{fmt(r.selection_rate, "%")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function CompanyTable({ rows }: { rows: CompanyStat[] }) {
  if (rows.length === 0) return null;
  return (
    <div>
      <h2 className="mb-2 text-lg font-semibold text-gray-900">
        Company leaderboard
      </h2>
      <div className="overflow-x-auto rounded-lg border border-gray-200">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50 text-left text-xs uppercase text-gray-500">
            <tr>
              <th className="px-3 py-2">Company</th>
              <th className="px-3 py-2">Drives</th>
              <th className="px-3 py-2">Applicants</th>
              <th className="px-3 py-2">Selected</th>
              <th className="px-3 py-2">Avg package</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {rows.map((c) => (
              <tr key={c.company_name}>
                <td className="px-3 py-2 font-medium text-gray-900">
                  {c.company_name}
                </td>
                <td className="px-3 py-2">{c.drives}</td>
                <td className="px-3 py-2">{c.applicants}</td>
                <td className="px-3 py-2 font-semibold">{c.selected}</td>
                <td className="px-3 py-2">{fmtLpa(c.avg_package)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
