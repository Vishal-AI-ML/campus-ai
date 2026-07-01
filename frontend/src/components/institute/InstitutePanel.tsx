"use client";

// Whole-institute KPI snapshot for the admin dashboard. Read-only: every number
// comes from the `/institute/dashboard` aggregation endpoint.
import { useEffect, useState } from "react";

import { ApiError } from "@/lib/api";
import {
  InstituteDashboard,
  fmt,
  getDashboard,
} from "@/components/institute/instituteApi";

// --- Small presentational helpers -----------------------------------------
function Stat({
  label,
  value,
  hint,
}: {
  label: string;
  value: string | number;
  hint?: string;
}) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4">
      <div className="text-2xl font-bold text-gray-900">{value}</div>
      <div className="mt-1 text-sm font-medium text-gray-700">{label}</div>
      {hint && <div className="mt-0.5 text-xs text-gray-400">{hint}</div>}
    </div>
  );
}

function Section({
  icon,
  title,
  children,
}: {
  icon: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="mb-8">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500">
        {icon} {title}
      </h2>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
        {children}
      </div>
    </section>
  );
}

// A verified/pending pair shown as one card (the anti-fraud moat view).
function MoatStat({
  label,
  verified,
  pending,
}: {
  label: string;
  verified: number;
  pending: number;
}) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4">
      <div className="text-2xl font-bold text-green-700">{verified}</div>
      <div className="mt-1 text-sm font-medium text-gray-700">{label}</div>
      <div className="mt-0.5 text-xs text-amber-600">{pending} pending</div>
    </div>
  );
}

export default function InstitutePanel() {
  const [data, setData] = useState<InstituteDashboard | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getDashboard()
      .then(setData)
      .catch((e) =>
        setError(
          e instanceof ApiError ? e.message : "Failed to load dashboard",
        ),
      );
  }, []);

  if (error) return <p className="text-sm text-red-600">{error}</p>;
  if (!data) return <p className="text-sm text-gray-500">Loading...</p>;

  const { users, structure, moat, academics, placement, engagement, risk } =
    data;

  return (
    <div>
      <Section icon="👥" title="People">
        <Stat label="Total accounts" value={users.total} />
        <Stat
          label="Active"
          value={users.active}
          hint={`${users.inactive} disabled`}
        />
        <Stat
          label="Students"
          value={users.students}
          hint={`${users.students_with_section} in a section`}
        />
        <Stat label="Teachers" value={users.teachers} />
        <Stat label="TPOs" value={users.tpos} />
        <Stat label="Admins" value={users.admins} />
        <Stat label="Recruiters" value={users.recruiters} />
      </Section>

      <Section icon="🏫" title="Structure">
        <Stat label="Departments" value={structure.departments} />
        <Stat label="Sections" value={structure.sections} />
        <Stat label="Subjects" value={structure.subjects} />
      </Section>

      <Section icon="🛡️" title="Verified-data moat">
        <MoatStat
          label="Skills"
          verified={moat.skills_verified}
          pending={moat.skills_pending}
        />
        <MoatStat
          label="Project roles"
          verified={moat.projects_verified}
          pending={moat.projects_pending}
        />
        <MoatStat
          label="Activities"
          verified={moat.eca_verified}
          pending={moat.eca_pending}
        />
        <MoatStat
          label="Internships"
          verified={moat.internships_verified}
          pending={moat.internships_pending}
        />
      </Section>

      <Section icon="📊" title="Academics (across sections)">
        <Stat
          label="Avg attendance"
          value={fmt(academics.avg_attendance_pct, "%")}
        />
        <Stat label="Avg CGPA" value={fmt(academics.avg_cgpa)} />
        <Stat
          label="Students graded"
          value={academics.students_with_results}
        />
      </Section>

      <Section icon="🏢" title="Placement">
        <Stat
          label="Drives"
          value={placement.total_drives}
          hint={`${placement.open_drives} open`}
        />
        <Stat label="Applications" value={placement.total_applications} />
        <Stat label="Placed students" value={placement.placed_students} />
        <Stat
          label="Placement rate"
          value={fmt(placement.placement_rate, "%")}
        />
        <Stat label="Avg package" value={fmt(placement.avg_package, " LPA")} />
        <Stat
          label="Highest package"
          value={fmt(placement.highest_package, " LPA")}
        />
        <Stat label="Recruiters" value={placement.recruiter_companies} />
      </Section>

      <Section icon="⚠️" title="At-risk students">
        <Stat label="High risk" value={risk.high} />
        <Stat label="Medium risk" value={risk.medium} />
        <Stat label="Low risk" value={risk.low} />
        <Stat label="Assessed" value={risk.assessed_students} />
      </Section>

      <Section icon="💬" title="Engagement">
        <Stat label="Assignments" value={engagement.assignments} />
        <Stat label="Submissions" value={engagement.submissions} />
        <Stat label="Materials" value={engagement.materials} />
        <Stat
          label="Doubts"
          value={engagement.doubts_open}
          hint={`${engagement.doubts_resolved} resolved`}
        />
        <Stat label="Announcements" value={engagement.announcements} />
        <Stat label="Leave queue" value={engagement.leave_pending} />
      </Section>

      <p className="mt-2 text-xs text-gray-400">
        Snapshot generated {new Date(data.generated_at).toLocaleString()}.
      </p>
    </div>
  );
}
