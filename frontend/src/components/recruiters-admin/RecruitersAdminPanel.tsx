"use client";

/**
 * Campus AI - TPO/admin Recruiter management portal (Step 27.5).
 *
 * Four cooperating sections:
 *   1. Onboard a company + invite its first HR (shows the one-time link).
 *   2. Companies onboarded so far (status badges).
 *   3. Invites (with revoke for still-pending ones).
 *   4. Link drives to a company + reveal/hide candidate contacts.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { ApiError } from "@/lib/api";
import {
  acceptUrl,
  APP_STATUS_STYLES,
  COMPANY_STYLES,
  fmtDate,
  fmtDateTime,
  INVITE_STYLES,
  inviteRecruiter,
  linkDriveToRecruiter,
  listDriveApplicants,
  listDrives,
  listInvites,
  listRecruiters,
  pretty,
  revokeInvite,
  setContactReveal,
  type Applicant,
  type Drive,
  type InviteCreated,
  type RecruiterCompany,
  type RecruiterInvite,
} from "./recruitersAdminApi";

function errText(e: unknown): string {
  if (e instanceof ApiError) return e.message;
  return e instanceof Error ? e.message : "Something went wrong";
}

export default function RecruitersAdminPanel() {
  const [companies, setCompanies] = useState<RecruiterCompany[]>([]);
  const [invites, setInvites] = useState<RecruiterInvite[]>([]);
  const [drives, setDrives] = useState<Drive[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [c, i, d] = await Promise.all([
        listRecruiters(),
        listInvites(),
        listDrives(),
      ]);
      setCompanies(c);
      setInvites(i);
      setDrives(d);
    } catch (e) {
      setError(errText(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  if (loading) {
    return <p className="mt-6 text-sm text-slate-400">Loading recruiters...</p>;
  }

  return (
    <div className="space-y-10">
      {error && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">
          {error}
        </div>
      )}

      <OnboardSection onDone={refresh} />

      <CompaniesSection companies={companies} />

      <InvitesSection invites={invites} onChanged={refresh} />

      <LinkDrivesSection
        drives={drives}
        companies={companies}
        onChanged={refresh}
      />

      <RevealContactSection drives={drives} companies={companies} />
    </div>
  );
}

/* ----------------------------- Onboard / invite -------------------------- */

function OnboardSection({ onDone }: { onDone: () => void }) {
  const [companyName, setCompanyName] = useState("");
  const [email, setEmail] = useState("");
  const [website, setWebsite] = useState("");
  const [title, setTitle] = useState("");
  const [about, setAbout] = useState("");
  const [expiresInDays, setExpiresInDays] = useState(14);
  const [submitting, setSubmitting] = useState(false);
  const [created, setCreated] = useState<InviteCreated | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setErr(null);
    setCreated(null);
    try {
      const res = await inviteRecruiter({
        company_name: companyName.trim(),
        email: email.trim(),
        website: website.trim() || null,
        title: title.trim() || null,
        about: about.trim() || null,
        expires_in_days: expiresInDays,
      });
      setCreated(res);
      setCompanyName("");
      setEmail("");
      setWebsite("");
      setTitle("");
      setAbout("");
      setExpiresInDays(14);
      onDone();
    } catch (e) {
      setErr(errText(e));
    } finally {
      setSubmitting(false);
    }
  }

  const link = created ? acceptUrl(created.accept_path) : "";

  async function copyLink() {
    try {
      await navigator.clipboard.writeText(link);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  }

  return (
    <section>
      <h3 className="text-lg font-semibold">🏢 Onboard a company</h3>
      <p className="mt-1 text-sm text-slate-400">
        Create the company and email a single-use invite link to its first HR.
      </p>

      <form
        onSubmit={submit}
        className="mt-4 grid gap-4 rounded-2xl border border-white/10 bg-white/5 p-5 sm:grid-cols-2"
      >
        <label className="text-sm">
          <span className="text-slate-400">Company name *</span>
          <input
            required
            value={companyName}
            onChange={(e) => setCompanyName(e.target.value)}
            className="mt-1 w-full rounded-lg border border-white/10 bg-slate-900/60 px-3 py-2 outline-none focus:border-white/30"
            placeholder="Acme Corp"
          />
        </label>
        <label className="text-sm">
          <span className="text-slate-400">HR email *</span>
          <input
            required
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1 w-full rounded-lg border border-white/10 bg-slate-900/60 px-3 py-2 outline-none focus:border-white/30"
            placeholder="hr@acme.com"
          />
        </label>
        <label className="text-sm">
          <span className="text-slate-400">Website</span>
          <input
            value={website}
            onChange={(e) => setWebsite(e.target.value)}
            className="mt-1 w-full rounded-lg border border-white/10 bg-slate-900/60 px-3 py-2 outline-none focus:border-white/30"
            placeholder="https://acme.com"
          />
        </label>
        <label className="text-sm">
          <span className="text-slate-400">HR title</span>
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="mt-1 w-full rounded-lg border border-white/10 bg-slate-900/60 px-3 py-2 outline-none focus:border-white/30"
            placeholder="Talent Acquisition Lead"
          />
        </label>
        <label className="text-sm sm:col-span-2">
          <span className="text-slate-400">About</span>
          <textarea
            value={about}
            onChange={(e) => setAbout(e.target.value)}
            rows={2}
            className="mt-1 w-full rounded-lg border border-white/10 bg-slate-900/60 px-3 py-2 outline-none focus:border-white/30"
            placeholder="Short description of the company."
          />
        </label>
        <label className="text-sm">
          <span className="text-slate-400">Invite valid for (days)</span>
          <input
            type="number"
            min={1}
            max={90}
            value={expiresInDays}
            onChange={(e) =>
              setExpiresInDays(Math.max(1, Math.min(90, Number(e.target.value))))
            }
            className="mt-1 w-full rounded-lg border border-white/10 bg-slate-900/60 px-3 py-2 outline-none focus:border-white/30"
          />
        </label>
        <div className="flex items-end">
          <button
            type="submit"
            disabled={submitting}
            className="rounded-lg bg-indigo-500 px-4 py-2 font-medium text-white transition hover:bg-indigo-400 disabled:opacity-50"
          >
            {submitting ? "Sending..." : "Create invite"}
          </button>
        </div>

        {err && (
          <p className="sm:col-span-2 text-sm text-red-300">{err}</p>
        )}
      </form>

      {created && (
        <div className="mt-4 rounded-2xl border border-emerald-500/30 bg-emerald-500/10 p-4">
          <p className="text-sm text-emerald-200">
            Invite created for <strong>{created.invite.email}</strong> at{" "}
            <strong>{created.recruiter.company_name}</strong>. Share this
            single-use link (valid till {fmtDate(created.invite.expires_at)}):
          </p>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <code className="flex-1 break-all rounded-lg bg-slate-900/70 px-3 py-2 text-xs text-slate-200">
              {link}
            </code>
            <button
              type="button"
              onClick={copyLink}
              className="rounded-lg border border-white/15 px-3 py-2 text-sm hover:bg-white/10"
            >
              {copied ? "Copied!" : "Copy"}
            </button>
          </div>
        </div>
      )}
    </section>
  );
}

/* ------------------------------- Companies ------------------------------- */

function CompaniesSection({
  companies,
}: {
  companies: RecruiterCompany[];
}) {
  return (
    <section>
      <h3 className="text-lg font-semibold">💼 Companies</h3>
      {companies.length === 0 ? (
        <p className="mt-2 text-sm text-slate-400">No companies onboarded yet.</p>
      ) : (
        <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {companies.map((c) => (
            <div
              key={c.id}
              className="rounded-2xl border border-white/10 bg-white/5 p-4"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-medium">{c.company_name}</span>
                <span
                  className={`rounded-full px-2 py-0.5 text-xs ${COMPANY_STYLES[c.status]}`}
                >
                  {pretty(c.status)}
                </span>
              </div>
              {c.website && (
                <a
                  href={c.website}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-1 block truncate text-xs text-sky-300 hover:underline"
                >
                  {c.website}
                </a>
              )}
              {c.about && (
                <p className="mt-2 text-xs text-slate-400 line-clamp-3">
                  {c.about}
                </p>
              )}
              <p className="mt-2 text-[11px] text-slate-500">
                Onboarded {fmtDate(c.created_at)}
              </p>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

/* -------------------------------- Invites -------------------------------- */

function InvitesSection({
  invites,
  onChanged,
}: {
  invites: RecruiterInvite[];
  onChanged: () => void;
}) {
  const [busyId, setBusyId] = useState<number | null>(null);
  const [err, setErr] = useState<string | null>(null);

  async function revoke(id: number) {
    setBusyId(id);
    setErr(null);
    try {
      await revokeInvite(id);
      onChanged();
    } catch (e) {
      setErr(errText(e));
    } finally {
      setBusyId(null);
    }
  }

  return (
    <section>
      <h3 className="text-lg font-semibold">📨 Invites</h3>
      {err && <p className="mt-2 text-sm text-red-300">{err}</p>}
      {invites.length === 0 ? (
        <p className="mt-2 text-sm text-slate-400">No invites yet.</p>
      ) : (
        <div className="mt-3 overflow-x-auto rounded-2xl border border-white/10">
          <table className="w-full text-left text-sm">
            <thead className="bg-white/5 text-slate-400">
              <tr>
                <th className="px-4 py-2 font-medium">Email</th>
                <th className="px-4 py-2 font-medium">Title</th>
                <th className="px-4 py-2 font-medium">Status</th>
                <th className="px-4 py-2 font-medium">Expires</th>
                <th className="px-4 py-2 font-medium">Accepted</th>
                <th className="px-4 py-2 font-medium"></th>
              </tr>
            </thead>
            <tbody>
              {invites.map((inv) => (
                <tr key={inv.id} className="border-t border-white/5">
                  <td className="px-4 py-2">{inv.email}</td>
                  <td className="px-4 py-2 text-slate-400">
                    {inv.title ?? "\u2014"}
                  </td>
                  <td className="px-4 py-2">
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs ${INVITE_STYLES[inv.status]}`}
                    >
                      {pretty(inv.status)}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-slate-400">
                    {fmtDate(inv.expires_at)}
                  </td>
                  <td className="px-4 py-2 text-slate-400">
                    {fmtDateTime(inv.accepted_at)}
                  </td>
                  <td className="px-4 py-2 text-right">
                    {inv.status === "pending" && (
                      <button
                        type="button"
                        onClick={() => revoke(inv.id)}
                        disabled={busyId === inv.id}
                        className="rounded-lg border border-red-500/30 px-3 py-1 text-xs text-red-300 hover:bg-red-500/10 disabled:opacity-50"
                      >
                        {busyId === inv.id ? "..." : "Revoke"}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

/* ------------------------------ Link drives ------------------------------ */

function LinkDrivesSection({
  drives,
  companies,
  onChanged,
}: {
  drives: Drive[];
  companies: RecruiterCompany[];
  onChanged: () => void;
}) {
  const [busyId, setBusyId] = useState<number | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const companyName = useMemo(() => {
    const map = new Map<number, string>();
    companies.forEach((c) => map.set(c.id, c.company_name));
    return map;
  }, [companies]);

  async function link(driveId: number, value: string) {
    setBusyId(driveId);
    setErr(null);
    try {
      await linkDriveToRecruiter(driveId, value ? Number(value) : null);
      onChanged();
    } catch (e) {
      setErr(errText(e));
    } finally {
      setBusyId(null);
    }
  }

  return (
    <section>
      <h3 className="text-lg font-semibold">🔗 Link drives to a company</h3>
      <p className="mt-1 text-sm text-slate-400">
        Once linked, the company&apos;s HR can view that drive&apos;s shortlisted
        and selected candidates.
      </p>
      {err && <p className="mt-2 text-sm text-red-300">{err}</p>}
      {drives.length === 0 ? (
        <p className="mt-2 text-sm text-slate-400">No drives posted yet.</p>
      ) : (
        <div className="mt-3 overflow-x-auto rounded-2xl border border-white/10">
          <table className="w-full text-left text-sm">
            <thead className="bg-white/5 text-slate-400">
              <tr>
                <th className="px-4 py-2 font-medium">Role</th>
                <th className="px-4 py-2 font-medium">Drive company</th>
                <th className="px-4 py-2 font-medium">Linked to</th>
                <th className="px-4 py-2 font-medium">Set company</th>
              </tr>
            </thead>
            <tbody>
              {drives.map((d) => (
                <tr key={d.id} className="border-t border-white/5">
                  <td className="px-4 py-2">{d.role_title}</td>
                  <td className="px-4 py-2 text-slate-400">{d.company_name}</td>
                  <td className="px-4 py-2">
                    {d.recruiter_id != null ? (
                      <span className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-xs text-emerald-300">
                        {companyName.get(d.recruiter_id) ?? `#${d.recruiter_id}`}
                      </span>
                    ) : (
                      <span className="text-xs text-slate-500">Not linked</span>
                    )}
                  </td>
                  <td className="px-4 py-2">
                    <select
                      value={d.recruiter_id ?? ""}
                      disabled={busyId === d.id}
                      onChange={(e) => link(d.id, e.target.value)}
                      className="rounded-lg border border-white/10 bg-slate-900/60 px-2 py-1 text-sm outline-none focus:border-white/30 disabled:opacity-50"
                    >
                      <option value="">Not linked</option>
                      {companies.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.company_name}
                        </option>
                      ))}
                    </select>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

/* ---------------------------- Reveal contact ----------------------------- */

function RevealContactSection({
  drives,
  companies,
}: {
  drives: Drive[];
  companies: RecruiterCompany[];
}) {
  // Only drives linked to a company are meaningful here.
  const linkedDrives = useMemo(
    () => drives.filter((d) => d.recruiter_id != null),
    [drives],
  );
  const [driveId, setDriveId] = useState<number | null>(null);
  const [applicants, setApplicants] = useState<Applicant[]>([]);
  const [loading, setLoading] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const companyName = useMemo(() => {
    const map = new Map<number, string>();
    companies.forEach((c) => map.set(c.id, c.company_name));
    return map;
  }, [companies]);

  const loadApplicants = useCallback(async (id: number) => {
    setLoading(true);
    setErr(null);
    try {
      const rows = await listDriveApplicants(id);
      // Recruiters only see shortlisted/selected; surface those first.
      setApplicants(
        rows.filter(
          (a) => a.status === "shortlisted" || a.status === "selected",
        ),
      );
    } catch (e) {
      setErr(errText(e));
      setApplicants([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (driveId != null) loadApplicants(driveId);
  }, [driveId, loadApplicants]);

  async function toggle(app: Applicant) {
    setBusyId(app.application_id);
    setErr(null);
    try {
      await setContactReveal(app.application_id, !app.contact_revealed);
      setApplicants((prev) =>
        prev.map((a) =>
          a.application_id === app.application_id
            ? { ...a, contact_revealed: !a.contact_revealed }
            : a,
        ),
      );
    } catch (e) {
      setErr(errText(e));
    } finally {
      setBusyId(null);
    }
  }

  return (
    <section>
      <h3 className="text-lg font-semibold">👁️ Reveal candidate contacts</h3>
      <p className="mt-1 text-sm text-slate-400">
        Pick a linked drive, then reveal a shortlisted candidate&apos;s contact
        so the company&apos;s HR can reach out.
      </p>

      {linkedDrives.length === 0 ? (
        <p className="mt-2 text-sm text-slate-400">
          Link a drive to a company first (section above).
        </p>
      ) : (
        <>
          <div className="mt-3">
            <select
              value={driveId ?? ""}
              onChange={(e) =>
                setDriveId(e.target.value ? Number(e.target.value) : null)
              }
              className="rounded-lg border border-white/10 bg-slate-900/60 px-3 py-2 text-sm outline-none focus:border-white/30"
            >
              <option value="">Select a drive...</option>
              {linkedDrives.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.role_title} → {companyName.get(d.recruiter_id!) ?? ""}
                </option>
              ))}
            </select>
          </div>

          {err && <p className="mt-2 text-sm text-red-300">{err}</p>}

          {driveId != null &&
            (loading ? (
              <p className="mt-3 text-sm text-slate-400">Loading candidates...</p>
            ) : applicants.length === 0 ? (
              <p className="mt-3 text-sm text-slate-400">
                No shortlisted or selected candidates on this drive yet.
              </p>
            ) : (
              <div className="mt-3 overflow-x-auto rounded-2xl border border-white/10">
                <table className="w-full text-left text-sm">
                  <thead className="bg-white/5 text-slate-400">
                    <tr>
                      <th className="px-4 py-2 font-medium">Candidate</th>
                      <th className="px-4 py-2 font-medium">Status</th>
                      <th className="px-4 py-2 font-medium">CGPA</th>
                      <th className="px-4 py-2 font-medium">Verified</th>
                      <th className="px-4 py-2 font-medium">Contact</th>
                      <th className="px-4 py-2 font-medium"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {applicants.map((a) => (
                      <tr
                        key={a.application_id}
                        className="border-t border-white/5"
                      >
                        <td className="px-4 py-2">{a.full_name}</td>
                        <td className="px-4 py-2">
                          <span
                            className={`rounded-full px-2 py-0.5 text-xs ${APP_STATUS_STYLES[a.status]}`}
                          >
                            {pretty(a.status)}
                          </span>
                        </td>
                        <td className="px-4 py-2 text-slate-400">{a.cgpa}</td>
                        <td className="px-4 py-2 text-slate-400">
                          {a.verified_skills} skills · {a.verified_projects}{" "}
                          proj
                        </td>
                        <td className="px-4 py-2">
                          {a.contact_revealed ? (
                            <span className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-xs text-emerald-300">
                              Revealed
                            </span>
                          ) : (
                            <span className="rounded-full bg-slate-500/15 px-2 py-0.5 text-xs text-slate-400">
                              Hidden
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-2 text-right">
                          <button
                            type="button"
                            onClick={() => toggle(a)}
                            disabled={busyId === a.application_id}
                            className={`rounded-lg border px-3 py-1 text-xs disabled:opacity-50 ${
                              a.contact_revealed
                                ? "border-white/15 hover:bg-white/10"
                                : "border-emerald-500/30 text-emerald-300 hover:bg-emerald-500/10"
                            }`}
                          >
                            {busyId === a.application_id
                              ? "..."
                              : a.contact_revealed
                                ? "Hide"
                                : "Reveal"}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ))}
        </>
      )}
    </section>
  );
}
