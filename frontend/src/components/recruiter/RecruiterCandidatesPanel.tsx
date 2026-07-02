"use client";

/**
 * Recruiter candidates panel (Step 27.4).
 *
 * Shows the shortlisted/selected candidates across the recruiter's linked
 * drives. Verified skills + projects are highlighted (the real hiring signal);
 * CGPA is a small secondary chip and attendance is intentionally not surfaced
 * as a primary metric. Each card lets the recruiter record a non-binding
 * decision (interested / on-hold / rejected) and extend a formal offer.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { ApiError } from "@/lib/api";
import {
  DECISION_STYLES,
  STATUS_STYLES,
  fmtPackage,
  pretty,
  extendOffer,
  listMyCandidates,
  listMyDrives,
  setDecision,
  type OfferCreate,
  type RecruiterCandidate,
  type RecruiterDecision,
  type RecruiterDrive,
} from "./recruiterApi";

type Filter = "all" | "shortlisted" | "selected";

export default function RecruiterCandidatesPanel() {
  const [drives, setDrives] = useState<RecruiterDrive[]>([]);
  const [candidates, setCandidates] = useState<RecruiterCandidate[]>([]);
  const [driveId, setDriveId] = useState<number | null>(null);
  const [statusFilter, setStatusFilter] = useState<Filter>("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [offerFor, setOfferFor] = useState<RecruiterCandidate | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [d, c] = await Promise.all([
        listMyDrives(),
        listMyCandidates({
          driveId,
          status: statusFilter === "all" ? null : statusFilter,
        }),
      ]);
      setDrives(d);
      setCandidates(c);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load candidates.");
    } finally {
      setLoading(false);
    }
  }, [driveId, statusFilter]);

  useEffect(() => {
    load();
  }, [load]);

  const summary = useMemo(() => {
    const shortlisted = candidates.filter((c) => c.status === "shortlisted").length;
    const selected = candidates.filter((c) => c.status === "selected").length;
    const offers = candidates.filter((c) => c.has_active_offer).length;
    return { shortlisted, selected, offers, total: candidates.length };
  }, [candidates]);

  function patchCandidate(updated: RecruiterCandidate) {
    setCandidates((prev) =>
      prev.map((c) =>
        c.application_id === updated.application_id ? updated : c,
      ),
    );
  }

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold">Candidates</h2>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Shortlisted &amp; selected students on your drives. Record a
            decision or extend an offer.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <select
            value={driveId ?? ""}
            onChange={(e) =>
              setDriveId(e.target.value ? Number(e.target.value) : null)
            }
            className="rounded-lg border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-900 px-3 py-2 text-sm"
          >
            <option value="">All drives</option>
            {drives.map((d) => (
              <option key={d.id} value={d.id}>
                {d.role_title}
              </option>
            ))}
          </select>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as Filter)}
            className="rounded-lg border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-900 px-3 py-2 text-sm"
          >
            <option value="all">All statuses</option>
            <option value="shortlisted">Shortlisted</option>
            <option value="selected">Selected</option>
          </select>
        </div>
      </div>

      {/* KPI strip */}
      <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Kpi label="Total visible" value={summary.total} accent="text-slate-900 dark:text-slate-100" />
        <Kpi label="Shortlisted" value={summary.shortlisted} accent="text-sky-600 dark:text-sky-300" />
        <Kpi label="Selected" value={summary.selected} accent="text-emerald-600 dark:text-emerald-300" />
        <Kpi label="With live offer" value={summary.offers} accent="text-indigo-600 dark:text-indigo-300" />
      </div>

      {error && (
        <p className="mt-6 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">
          {error}
        </p>
      )}

      {loading ? (
        <p className="mt-8 text-sm text-slate-500 dark:text-slate-400">Loading candidates...</p>
      ) : candidates.length === 0 ? (
        <div className="mt-8 rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-900 p-8 text-center text-slate-500 dark:text-slate-400">
          No candidates are visible yet. The TPO shortlists or selects students
          on your linked drives before they appear here.
        </div>
      ) : (
        <div className="mt-6 grid gap-4 lg:grid-cols-2">
          {candidates.map((c) => (
            <CandidateCard
              key={c.application_id}
              candidate={c}
              onChanged={patchCandidate}
              onExtend={() => setOfferFor(c)}
            />
          ))}
        </div>
      )}

      {offerFor && (
        <OfferModal
          candidate={offerFor}
          drives={drives}
          onClose={() => setOfferFor(null)}
          onCreated={() => {
            setOfferFor(null);
            load();
          }}
        />
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
  value: number;
  accent: string;
}) {
  return (
    <div className="rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-900 p-4">
      <div className={`text-2xl font-bold ${accent}`}>{value}</div>
      <div className="mt-1 text-xs text-slate-500 dark:text-slate-400">{label}</div>
    </div>
  );
}

const DECISIONS: Exclude<RecruiterDecision, "pending">[] = [
  "interested",
  "on_hold",
  "rejected",
];

function CandidateCard({
  candidate,
  onChanged,
  onExtend,
}: {
  candidate: RecruiterCandidate;
  onChanged: (c: RecruiterCandidate) => void;
  onExtend: () => void;
}) {
  const [saving, setSaving] = useState<RecruiterDecision | null>(null);
  const [note, setNote] = useState(candidate.recruiter_decision_note ?? "");
  const [err, setErr] = useState<string | null>(null);

  async function decide(decision: Exclude<RecruiterDecision, "pending">) {
    setSaving(decision);
    setErr(null);
    try {
      const updated = await setDecision(
        candidate.application_id,
        decision,
        note.trim() || undefined,
      );
      onChanged(updated);
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "Could not save decision.");
    } finally {
      setSaving(null);
    }
  }

  return (
    <div className="rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-900 p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-lg font-semibold">{candidate.full_name}</span>
            <span
              className={`rounded-full px-2 py-0.5 text-xs ${STATUS_STYLES[candidate.status]}`}
            >
              {pretty(candidate.status)}
            </span>
          </div>
          <p className="mt-0.5 text-sm text-slate-500 dark:text-slate-400">{candidate.drive_role}</p>
        </div>
        <span
          className={`rounded-full px-2 py-0.5 text-xs ${DECISION_STYLES[candidate.recruiter_decision]}`}
        >
          {pretty(candidate.recruiter_decision)}
        </span>
      </div>

      {/* Verified signal (highlighted) */}
      <div className="mt-4">
        <div className="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400">
          Verified skills
        </div>
        <div className="mt-1 flex flex-wrap gap-1.5">
          {candidate.verified_skills.length === 0 ? (
            <span className="text-sm text-slate-500 dark:text-slate-400">None verified yet</span>
          ) : (
            candidate.verified_skills.map((s) => (
              <span
                key={s}
                className="rounded-md bg-emerald-500/15 px-2 py-0.5 text-sm text-emerald-200"
              >
                {s}
              </span>
            ))
          )}
        </div>
        <div className="mt-3 flex items-center gap-4">
          <div className="rounded-lg bg-white dark:bg-slate-900 px-3 py-2">
            <span className="text-lg font-semibold text-violet-600 dark:text-violet-300">
              {candidate.verified_projects}
            </span>{" "}
            <span className="text-xs text-slate-500 dark:text-slate-400">verified projects</span>
          </div>
          {/* CGPA is secondary, muted context only */}
          <span className="text-xs text-slate-500 dark:text-slate-400">
            CGPA {candidate.cgpa.toFixed(2)}
          </span>
        </div>
      </div>

      {/* Verified extra-curriculars (well-rounded signal) */}
      <div className="mt-4">
        <div className="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400">
          Verified activities
        </div>
        <div className="mt-1 flex flex-wrap gap-1.5">
          {(candidate.verified_eca ?? []).length === 0 ? (
            <span className="text-sm text-slate-500 dark:text-slate-400">None verified yet</span>
          ) : (
            (candidate.verified_eca ?? []).map((a) => (
              <span
                key={a}
                className="rounded-md bg-sky-500/15 px-2 py-0.5 text-sm text-sky-200"
              >
                {a}
              </span>
            ))
          )}
        </div>
      </div>

      {/* Verified internships / OJT (real work experience) */}
      <div className="mt-4">
        <div className="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400">
          Verified internships
        </div>
        <div className="mt-1 flex flex-wrap gap-1.5">
          {(candidate.verified_internships ?? []).length === 0 ? (
            <span className="text-sm text-slate-500 dark:text-slate-400">None verified yet</span>
          ) : (
            (candidate.verified_internships ?? []).map((i) => (
              <span
                key={i}
                className="rounded-md bg-amber-500/15 px-2 py-0.5 text-sm text-amber-200"
              >
                {i}
              </span>
            ))
          )}
        </div>
      </div>

      {/* Contact (only when TPO revealed it) */}
      <div className="mt-4 text-sm">
        {candidate.contact_revealed && candidate.email ? (
          <a
            href={`mailto:${candidate.email}`}
            className="text-indigo-600 dark:text-indigo-300 hover:underline"
          >
            {candidate.email}
          </a>
        ) : (
          <span className="text-slate-500 dark:text-slate-400">Contact hidden by TPO</span>
        )}
      </div>

      {/* Decision controls */}
      <div className="mt-4 border-t border-slate-200 dark:border-white/10 pt-4">
        <input
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="Decision note (optional)"
          className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-900 px-3 py-2 text-sm"
        />
        <div className="mt-2 flex flex-wrap items-center gap-2">
          {DECISIONS.map((d) => (
            <button
              key={d}
              onClick={() => decide(d)}
              disabled={saving !== null}
              className={`rounded-lg px-3 py-1.5 text-sm transition disabled:opacity-50 ${
                candidate.recruiter_decision === d
                  ? "bg-indigo-500 text-white"
                  : "border border-slate-300 dark:border-white/15 hover:bg-slate-100 dark:hover:bg-white/10"
              }`}
            >
              {saving === d ? "Saving..." : pretty(d)}
            </button>
          ))}
          <button
            onClick={onExtend}
            disabled={candidate.has_active_offer}
            className="ml-auto rounded-lg bg-gradient-to-r from-indigo-500 to-violet-500 px-3 py-1.5 text-sm font-medium text-white transition hover:opacity-90 disabled:opacity-50"
          >
            {candidate.has_active_offer ? "Offer live" : "Extend offer"}
          </button>
        </div>
        {err && <p className="mt-2 text-sm text-red-300">{err}</p>}
      </div>
    </div>
  );
}

function OfferModal({
  candidate,
  drives,
  onClose,
  onCreated,
}: {
  candidate: RecruiterCandidate;
  drives: RecruiterDrive[];
  onClose: () => void;
  onCreated: () => void;
}) {
  const drive = drives.find((d) => d.id === candidate.drive_id);
  const [roleTitle, setRoleTitle] = useState(candidate.drive_role);
  const [packageLpa, setPackageLpa] = useState(
    drive?.package_lpa != null ? String(drive.package_lpa) : "",
  );
  const [location, setLocation] = useState(drive?.location ?? "");
  const [joiningDate, setJoiningDate] = useState("");
  const [expiresOn, setExpiresOn] = useState("");
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function submit() {
    setSaving(true);
    setErr(null);
    try {
      const payload: OfferCreate = {
        application_id: candidate.application_id,
        role_title: roleTitle.trim() || null,
        package_lpa: packageLpa.trim() ? Number(packageLpa) : null,
        location: location.trim() || null,
        joining_date: joiningDate || null,
        expires_on: expiresOn || null,
        note: note.trim() || null,
      };
      await extendOffer(payload);
      onCreated();
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "Could not extend offer.");
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="w-full max-w-md rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-900 p-6">
        <h3 className="text-lg font-semibold">Extend offer</h3>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          To {candidate.full_name} — blanks fall back to the drive&apos;s
          terms.
        </p>

        <div className="mt-4 space-y-3">
          <Field label="Role title">
            <input
              value={roleTitle}
              onChange={(e) => setRoleTitle(e.target.value)}
              className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-slate-950 px-3 py-2 text-sm"
            />
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Package (LPA)">
              <input
                type="number"
                step="0.1"
                min="0"
                value={packageLpa}
                onChange={(e) => setPackageLpa(e.target.value)}
                className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-slate-950 px-3 py-2 text-sm"
              />
            </Field>
            <Field label="Location">
              <input
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-slate-950 px-3 py-2 text-sm"
              />
            </Field>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Joining date">
              <input
                type="date"
                value={joiningDate}
                onChange={(e) => setJoiningDate(e.target.value)}
                className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-slate-950 px-3 py-2 text-sm"
              />
            </Field>
            <Field label="Expires on">
              <input
                type="date"
                value={expiresOn}
                onChange={(e) => setExpiresOn(e.target.value)}
                className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-slate-950 px-3 py-2 text-sm"
              />
            </Field>
          </div>
          <Field label="Note">
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              rows={2}
              className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-slate-950 px-3 py-2 text-sm"
            />
          </Field>
        </div>

        {err && <p className="mt-3 text-sm text-red-300">{err}</p>}

        <div className="mt-5 flex justify-end gap-2">
          <button
            onClick={onClose}
            disabled={saving}
            className="rounded-lg border border-slate-300 dark:border-white/15 px-4 py-2 text-sm hover:bg-slate-100 dark:hover:bg-white/10 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={submit}
            disabled={saving}
            className="rounded-lg bg-gradient-to-r from-indigo-500 to-violet-500 px-4 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
          >
            {saving ? "Extending..." : `Extend (${fmtPackage(
              packageLpa.trim() ? Number(packageLpa) : drive?.package_lpa ?? null,
            )})`}
          </button>
        </div>
      </div>
    </div>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className="block text-xs font-medium text-slate-500 dark:text-slate-400">{label}</span>
      <div className="mt-1">{children}</div>
    </label>
  );
}
