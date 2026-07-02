/**
 * Recruiter \u2192 Offers page (Step 27.4).
 *
 * Place this file at: src/app/dashboard/recruiter-offers/page.tsx
 */

"use client";

import { useCurrentUser } from "@/lib/auth";
import RecruiterOffersPanel from "@/components/recruiter/RecruiterOffersPanel";

export default function RecruiterOffersPage() {
  const { user } = useCurrentUser();
  if (!user) return null;
  if (user.role !== "recruiter") {
    return (
      <p className="text-sm text-slate-500 dark:text-slate-400">
        This page is only available to recruiter accounts.
      </p>
    );
  }
  return <RecruiterOffersPanel />;
}
