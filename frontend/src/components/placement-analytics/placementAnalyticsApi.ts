// Typed API helpers + shared types for the Placement Analytics (TPO) module.
// Mirrors the backend `/placement/analytics` routes (read-only aggregation).
import { api } from "@/lib/api";

export type Role = "student" | "teacher" | "tpo" | "admin";

export type MeUser = {
  id: number;
  email: string;
  full_name: string;
  role: Role;
};

export type PlacementFunnel = {
  applied: number;
  shortlisted: number;
  selected: number;
  rejected: number;
};

export type DrivePerformance = {
  drive_id: number;
  company_name: string;
  role_title: string;
  package_lpa: number | null;
  is_open: boolean;
  applicants: number;
  shortlisted: number;
  selected: number;
  rejected: number;
  selection_rate: number | null;
};

export type CompanyStat = {
  company_name: string;
  drives: number;
  applicants: number;
  selected: number;
  avg_package: number | null;
};

export type PlacementAnalytics = {
  total_drives: number;
  open_drives: number;
  closed_drives: number;
  total_applications: number;
  unique_applicants: number;
  placed_students: number;
  total_active_students: number;
  placement_rate: number | null;
  applicant_conversion: number | null;
  avg_package: number | null;
  highest_package: number | null;
  highest_package_company: string | null;
  funnel: PlacementFunnel;
  drives: DrivePerformance[];
  companies: CompanyStat[];
};

// Funnel steps drive both the stacked bar and the legend chips.
export const FUNNEL_STEPS = [
  {
    key: "applied",
    label: "Applied",
    bar: "bg-sky-500",
    chip: "bg-sky-100 text-sky-800",
  },
  {
    key: "shortlisted",
    label: "Shortlisted",
    bar: "bg-amber-500",
    chip: "bg-amber-100 text-amber-800",
  },
  {
    key: "selected",
    label: "Selected",
    bar: "bg-green-500",
    chip: "bg-green-100 text-green-800",
  },
  {
    key: "rejected",
    label: "Rejected",
    bar: "bg-red-500",
    chip: "bg-red-100 text-red-800",
  },
] as const;

// Show "—" for missing numbers; otherwise append an optional suffix.
export function fmt(value: number | null, suffix = ""): string {
  return value == null ? "—" : `${value}${suffix}`;
}

// Format a CTC value in lakhs-per-annum, or "—" when unknown.
export function fmtLpa(value: number | null): string {
  return value == null ? "—" : `${value} LPA`;
}

export function getMe(): Promise<MeUser> {
  return api.get("/auth/me") as Promise<MeUser>;
}

export function getOverview(): Promise<PlacementAnalytics> {
  return api.get(
    "/placement/analytics/overview",
  ) as Promise<PlacementAnalytics>;
}
