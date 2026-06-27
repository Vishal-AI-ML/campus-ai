"use client";

/**
 * Campus AI - TPO/admin Recruiter management (Step 27.5).
 *
 * Route: /dashboard/recruiters
 * Guarded to staff (tpo / admin); the dashboard layout already wraps this in
 * <AuthProvider><AppShell>.
 */

import { useCurrentUser } from "@/lib/auth";
import RecruitersAdminPanel from "@/components/recruiters-admin/RecruitersAdminPanel";

export default function RecruitersAdminPage() {
  const { user } = useCurrentUser();
  if (!user) return null;

  if (user.role !== "tpo" && user.role !== "admin") {
    return (
      <div>
        <h2 className="text-2xl font-bold">Recruiters</h2>
        <p className="mt-2 text-slate-400">
          This page is only available to placement staff.
        </p>
      </div>
    );
  }

  return (
    <div>
      <h2 className="text-3xl font-bold">Recruiters</h2>
      <p className="mt-2 text-slate-400">
        Onboard companies, link drives and control candidate contact visibility.
      </p>
      <div className="mt-8">
        <RecruitersAdminPanel />
      </div>
    </div>
  );
}
