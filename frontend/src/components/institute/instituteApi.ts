// Typed API helpers + shared types for the Institute Dashboard (admin module).
// Mirrors the backend `/institute/dashboard` route (read-only aggregation).
import { api } from "@/lib/api";

export type Role = "student" | "teacher" | "tpo" | "admin" | "recruiter";

export type MeUser = {
  id: number;
  email: string;
  full_name: string;
  role: Role;
};

export type InstituteUsers = {
  total: number;
  active: number;
  inactive: number;
  students: number;
  teachers: number;
  tpos: number;
  admins: number;
  recruiters: number;
  students_with_section: number;
};

export type InstituteStructure = {
  departments: number;
  sections: number;
  subjects: number;
};

export type InstituteMoat = {
  skills_verified: number;
  skills_pending: number;
  projects_verified: number;
  projects_pending: number;
  eca_verified: number;
  eca_pending: number;
  internships_verified: number;
  internships_pending: number;
};

export type InstituteAcademics = {
  avg_attendance_pct: number | null;
  students_with_results: number;
  avg_cgpa: number | null;
};

export type InstitutePlacement = {
  total_drives: number;
  open_drives: number;
  total_applications: number;
  placed_students: number;
  placement_rate: number | null;
  avg_package: number | null;
  highest_package: number | null;
  recruiter_companies: number;
};

export type InstituteEngagement = {
  assignments: number;
  submissions: number;
  materials: number;
  doubts_open: number;
  doubts_resolved: number;
  announcements: number;
  leave_pending: number;
};

export type InstituteRisk = {
  assessed_students: number;
  high: number;
  medium: number;
  low: number;
};

export type InstituteDashboard = {
  generated_at: string;
  users: InstituteUsers;
  structure: InstituteStructure;
  moat: InstituteMoat;
  academics: InstituteAcademics;
  placement: InstitutePlacement;
  engagement: InstituteEngagement;
  risk: InstituteRisk;
};

// Show "\u2014" for missing numbers; otherwise append an optional suffix.
export function fmt(value: number | null | undefined, suffix = ""): string {
  return value == null ? "\u2014" : `${value}${suffix}`;
}

export function getMe(): Promise<MeUser> {
  return api.get("/auth/me") as Promise<MeUser>;
}

export function getDashboard(): Promise<InstituteDashboard> {
  return api.get("/institute/dashboard") as Promise<InstituteDashboard>;
}
