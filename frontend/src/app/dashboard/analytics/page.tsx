"use client";

// Route: /dashboard/analytics
// Role-aware: staff (teacher/admin/tpo) see class analytics + at-risk;
// students see their own risk self-assessment.
import { useEffect, useState } from "react";

import { ApiError } from "@/lib/api";
import { MeUser, getMe } from "@/components/analytics/analyticsApi";
import ClassAnalyticsPanel from "@/components/analytics/ClassAnalyticsPanel";
import MyRiskPanel from "@/components/analytics/MyRiskPanel";

const ICON = "\u{1F4C8}";

export default function AnalyticsPage() {
  const [me, setMe] = useState<MeUser | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getMe()
      .then(setMe)
      .catch((e) =>
        setError(e instanceof ApiError ? e.message : "Failed to load profile"),
      );
  }, []);

  const isStaff =
    me?.role === "teacher" || me?.role === "admin" || me?.role === "tpo";

  return (
    <div className="mx-auto max-w-4xl p-6">
      <h1 className="mb-1 text-2xl font-bold text-gray-900 dark:text-slate-100">
        {ICON} {isStaff ? "Class Analytics" : "My Risk"}
      </h1>
      <p className="mb-6 text-sm text-gray-500 dark:text-slate-400">
        {isStaff
          ? "Class health + explainable at-risk students (attendance, CGPA, submissions)."
          : "Your early-warning risk score, with a transparent breakdown."}
      </p>
      {error && <p className="text-sm text-red-600">{error}</p>}
      {!me ? (
        <p className="text-sm text-gray-500 dark:text-slate-400">Loading...</p>
      ) : isStaff ? (
        <ClassAnalyticsPanel />
      ) : (
        <MyRiskPanel />
      )}
    </div>
  );
}
