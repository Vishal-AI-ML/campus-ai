// Typed API helpers + shared types for the Recruiter portal (Step 27.4).
// Mirrors the backend `/recruiters` routes a recruiter account can call.
import { api } from "@/lib/api";

export type RecruiterStatus = "pending" | "active" | "suspended";
export type ApplicationStatus =
  | "applied"
  | "shortlisted"
  | "selected"
  | "rejected";
export type RecruiterDecision =
  | "pending"
  | "interested"
  | "on_hold"
  | "rejected";
export type OfferStatus = "extended" | "accepted" | "declined" | "withdrawn";

export type RecruiterCompany = {
  id: number;
  company_name: string;
  website: string | null;
  about: string | null;
  status: RecruiterStatus;
  created_at: string;
};

export type RecruiterMe = {
  user: { id: number; email: string; full_name: string; role: string };
  recruiter: RecruiterCompany;
  title: string | null;
  is_primary: boolean;
};

export type RecruiterDrive = {
  id: number;
  company_name: string;
  role_title: string;
  location: string | null;
  package_lpa: number | null;
  is_open: boolean;
  deadline: string | null;
  shortlisted_count: number;
  selected_count: number;
};

export type RecruiterCandidate = {
  application_id: number;
  drive_id: number;
  drive_role: string;
  status: ApplicationStatus;
  full_name: string;
  cgpa: number;
  attendance: number;
  verified_skills: string[];
  verified_projects: number;
  verified_eca: string[];
  contact_revealed: boolean;
  email: string | null;
  recruiter_decision: RecruiterDecision;
  recruiter_decision_note: string | null;
  has_active_offer: boolean;
};

export type Offer = {
  id: number;
  application_id: number;
  drive_id: number;
  drive_role: string;
  company_name: string;
  student_id: number;
  student_name: string;
  role_title: string;
  package_lpa: number | null;
  location: string | null;
  joining_date: string | null;
  expires_on: string | null;
  status: OfferStatus;
  note: string | null;
  student_response_note: string | null;
  created_at: string;
  responded_at: string | null;
};

export type OfferCreate = {
  application_id: number;
  role_title?: string | null;
  package_lpa?: number | null;
  location?: string | null;
  joining_date?: string | null;
  expires_on?: string | null;
  note?: string | null;
};

// ----- presentation helpers ------------------------------------------------

export const DECISION_STYLES: Record<RecruiterDecision, string> = {
  pending: "bg-slate-500/15 text-slate-300",
  interested: "bg-emerald-500/15 text-emerald-300",
  on_hold: "bg-amber-500/15 text-amber-300",
  rejected: "bg-red-500/15 text-red-300",
};

export const OFFER_STYLES: Record<OfferStatus, string> = {
  extended: "bg-indigo-500/15 text-indigo-300",
  accepted: "bg-emerald-500/15 text-emerald-300",
  declined: "bg-red-500/15 text-red-300",
  withdrawn: "bg-slate-500/15 text-slate-400",
};

export const STATUS_STYLES: Record<ApplicationStatus, string> = {
  applied: "bg-slate-500/15 text-slate-300",
  shortlisted: "bg-sky-500/15 text-sky-300",
  selected: "bg-emerald-500/15 text-emerald-300",
  rejected: "bg-red-500/15 text-red-300",
};

/** Pretty-print an enum value like "on_hold" -> "On Hold". */
export function pretty(value: string): string {
  return value
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

export function fmtPackage(lpa: number | null): string {
  return lpa == null ? "\u2014" : `${lpa} LPA`;
}

export function fmtDate(iso: string | null): string {
  if (!iso) return "\u2014";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString();
}

// ----- API calls -----------------------------------------------------------

export function getRecruiterMe(): Promise<RecruiterMe> {
  return api.get("/recruiters/me") as Promise<RecruiterMe>;
}

export function listMyDrives(): Promise<RecruiterDrive[]> {
  return api.get("/recruiters/me/drives") as Promise<RecruiterDrive[]>;
}

export function listMyCandidates(params?: {
  driveId?: number | null;
  status?: "shortlisted" | "selected" | null;
}): Promise<RecruiterCandidate[]> {
  const q = new URLSearchParams();
  if (params?.driveId != null) q.set("drive_id", String(params.driveId));
  if (params?.status) q.set("status_filter", params.status);
  const qs = q.toString();
  return api.get(
    `/recruiters/me/candidates${qs ? `?${qs}` : ""}`,
  ) as Promise<RecruiterCandidate[]>;
}

export function setDecision(
  applicationId: number,
  decision: Exclude<RecruiterDecision, "pending">,
  note?: string,
): Promise<RecruiterCandidate> {
  return api.patch(`/recruiters/me/candidates/${applicationId}/decision`, {
    decision,
    note: note || null,
  }) as Promise<RecruiterCandidate>;
}

export function extendOffer(payload: OfferCreate): Promise<Offer> {
  return api.post("/recruiters/me/offers", payload) as Promise<Offer>;
}

export function listMyOffers(): Promise<Offer[]> {
  return api.get("/recruiters/me/offers") as Promise<Offer[]>;
}

export function withdrawOffer(offerId: number): Promise<Offer> {
  return api.patch(
    `/recruiters/me/offers/${offerId}/withdraw`,
  ) as Promise<Offer>;
}
