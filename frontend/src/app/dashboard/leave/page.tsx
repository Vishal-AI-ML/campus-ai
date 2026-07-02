"use client";

// Route: /dashboard/leave
// Role-aware: students apply + track; staff (teacher/admin/tpo) approve + bulk OD.
import { useEffect, useState } from "react";

import { ApiError } from "@/lib/api";
import { MeUser, getMe } from "@/components/leaveod/leaveodApi";
import LeaveStaffPanel from "@/components/leaveod/LeaveStaffPanel";
import LeaveStudentPanel from "@/components/leaveod/LeaveStudentPanel";

const ICON = "\u{1F3D6}\uFE0F";

export default function LeavePage() {
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
    <div className="mx-auto max-w-3xl p-6">
      <h1 className="mb-1 text-2xl font-bold text-gray-900 dark:text-slate-100">
        {ICON} Leave &amp; OD
      </h1>
      <p className="mb-6 text-sm text-gray-500 dark:text-slate-400">
        {isStaff
          ? "Review leave / OD requests and raise bulk OD for events."
          : "Apply for leave or on-duty (OD) and track your requests."}
      </p>
      {error && <p className="text-sm text-red-600">{error}</p>}
      {!me ? (
        <p className="text-sm text-gray-500 dark:text-slate-400">Loading...</p>
      ) : isStaff ? (
        <LeaveStaffPanel />
      ) : (
        <LeaveStudentPanel />
      )}
    </div>
  );
}
