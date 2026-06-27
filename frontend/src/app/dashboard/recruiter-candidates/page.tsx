/**
 * Recruiter \u2192 Candidates page (Step 27.4).
 *
 * Place this file at: src/app/dashboard/recruiter-candidates/page.tsx
 */

"use client";

import { useCurrentUser } from "@/lib/auth";
import RecruiterCandidatesPanel from "@/components/recruiter/RecruiterCandidatesPanel";

export default function RecruiterCandidatesPage() {
  const { user } = useCurrentUser();
  if (!user) return null;
  if (user.role !== "recruiter") {
    return (
      <p className="text-sm text-slate-400">
        This page is only available to recruiter accounts.
      </p>
    );
  }
  return <RecruiterCandidatesPanel />;
}
