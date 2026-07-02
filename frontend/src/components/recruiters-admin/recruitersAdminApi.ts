// Typed API helpers + shared types for the TPO/admin Recruiter management
// portal (Step 27.5). Mirrors the staff-only `/recruiters` and `/drives`
// routes used to onboard companies, link drives and reveal candidate contacts.
import { api } from "@/lib/api";

export type RecruiterStatus = "pending" | "active" | "suspended";
export type InviteStatus = "pending" | "accepted" | "revoked" | "expired";
export type ApplicationStatus =
  | "applied"
  | "shortlisted"
  | "selected"
  | "rejected";

export type RecruiterCompany = {
  id: number;
  company_name: string;
  website: string | null;
  about: string | null;
  status: RecruiterStatus;
  created_at: string;
};

export type RecruiterInvite = {
  id: number;
  recruiter_id: number;
  email: string;
  status: InviteStatus;
  title: string | null;
  expires_at: string;
  accepted_at: string | null;
  created_at: string;
};

export type InviteCreatePayload = {
  company_name: string;
  email: string;
  website?: string | null;
  about?: string | null;
  title?: string | null;
  expires_in_days?: number;
};

export type InviteCreated = {
  invite: RecruiterInvite;
  recruiter: RecruiterCompany;
  token: string;
  accept_path: string;
};

export type Drive = {
  id: number;
  company_name: string;
  role_title: string;
  description: string | null;
  location: string | null;
  package_lpa: number | null;
  min_cgpa: number;
  min_attendance: number;
  min_verified_projects: number;
  required_skills: string | null;
  is_open: boolean;
  deadline: string | null;
  recruiter_id: number | null;
};

export type Applicant = {
  application_id: number;
  student_id: number;
  full_name: string;
  status: ApplicationStatus;
  eligible: boolean;
  cgpa: number;
  attendance: number;
  verified_skills: number;
  verified_projects: number;
  note: string | null;
  contact_revealed: boolean;
};

// ----- presentation helpers ------------------------------------------------

export const COMPANY_STYLES: Record<RecruiterStatus, string> = {
  pending: "bg-amber-500/15 text-amber-600 dark:text-amber-300",
  active: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-300",
  suspended: "bg-red-500/15 text-red-300",
};

export const INVITE_STYLES: Record<InviteStatus, string> = {
  pending: "bg-amber-500/15 text-amber-600 dark:text-amber-300",
  accepted: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-300",
  revoked: "bg-slate-500/15 text-slate-500 dark:text-slate-400",
  expired: "bg-red-500/15 text-red-300",
};

export const APP_STATUS_STYLES: Record<ApplicationStatus, string> = {
  applied: "bg-slate-500/15 text-slate-600 dark:text-slate-300",
  shortlisted: "bg-sky-500/15 text-sky-600 dark:text-sky-300",
  selected: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-300",
  rejected: "bg-red-500/15 text-red-300",
};

export function pretty(value: string): string {
  return value
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

export function fmtDate(iso: string | null): string {
  if (!iso) return "\u2014";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString();
}

export function fmtDateTime(iso: string | null): string {
  if (!iso) return "\u2014";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString();
}

/** Build the full invite-accept URL the recruiter should open. */
export function acceptUrl(acceptPath: string): string {
  if (typeof window === "undefined") return acceptPath;
  return `${window.location.origin}${acceptPath}`;
}

// ----- API calls -----------------------------------------------------------

export function listRecruiters(): Promise<RecruiterCompany[]> {
  return api.get("/recruiters") as Promise<RecruiterCompany[]>;
}

export function listInvites(): Promise<RecruiterInvite[]> {
  return api.get("/recruiters/invites") as Promise<RecruiterInvite[]>;
}

export function inviteRecruiter(
  payload: InviteCreatePayload,
): Promise<InviteCreated> {
  return api.post("/recruiters/invite", payload) as Promise<InviteCreated>;
}

export function revokeInvite(inviteId: number): Promise<RecruiterInvite> {
  return api.post(
    `/recruiters/invites/${inviteId}/revoke`,
  ) as Promise<RecruiterInvite>;
}

export function listDrives(): Promise<Drive[]> {
  return api.get("/drives") as Promise<Drive[]>;
}

export function linkDriveToRecruiter(
  driveId: number,
  recruiterId: number | null,
): Promise<Drive> {
  return api.patch(`/recruiters/drives/${driveId}/recruiter`, {
    recruiter_id: recruiterId,
  }) as Promise<Drive>;
}

export function listDriveApplicants(
  driveId: number,
  statusFilter?: ApplicationStatus | null,
): Promise<Applicant[]> {
  const qs = statusFilter ? `?status_filter=${statusFilter}` : "";
  return api.get(`/drives/${driveId}/applications${qs}`) as Promise<Applicant[]>;
}

export function setContactReveal(
  applicationId: number,
  revealed: boolean,
): Promise<unknown> {
  return api.patch(`/recruiters/applications/${applicationId}/contact`, {
    revealed,
  });
}
