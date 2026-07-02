"use client";

// Route: /dashboard/institute
// Admin: institute-wide KPI snapshot (people, moat, academics, placement,
// engagement, at-risk) rolled up from data the institute already trusts.
import { useEffect, useState } from "react";

import { ApiError } from "@/lib/api";
import { MeUser, getMe } from "@/components/institute/instituteApi";
import InstitutePanel from "@/components/institute/InstitutePanel";

const ICON = "\u{1F3DB}\uFE0F";

export default function InstitutePage() {
  const [me, setMe] = useState<MeUser | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getMe()
      .then(setMe)
      .catch((e) =>
        setError(e instanceof ApiError ? e.message : "Failed to load profile"),
      );
  }, []);

  return (
    <div className="mx-auto max-w-5xl p-6">
      <h1 className="mb-1 text-2xl font-bold text-gray-900 dark:text-slate-100">
        {ICON} Institute Dashboard
      </h1>
      <p className="mb-6 text-sm text-gray-500 dark:text-slate-400">
        A whole-institute KPI snapshot: people, the verified-data moat,
        academics, placement, engagement, and at-risk students.
      </p>
      {error && <p className="text-sm text-red-600">{error}</p>}
      {!me ? (
        <p className="text-sm text-gray-500 dark:text-slate-400">Loading...</p>
      ) : me.role === "admin" ? (
        <InstitutePanel />
      ) : (
        <p className="text-sm text-gray-500 dark:text-slate-400">
          The institute dashboard is available to administrators only.
        </p>
      )}
    </div>
  );
}
