// Typed API helpers + shared types for the Analytics / At-risk module.
// Mirrors the backend `/analytics` routes (class dashboard + explainable risk).
import { api } from "@/lib/api";

export type Role = "student" | "teacher" | "tpo" | "admin";

export type MeUser = {
  id: number;
  email: string;
  full_name: string;
  role: Role;
  section_id: number | null;
};

export type Department = { id: number; name: string; code: string };
export type Section = {
  id: number;
  name: string;
  year: number | null;
  department_id: number;
};

export type RiskBand = "high" | "medium" | "low";

export type RiskFactor = {
  key: string;
  label: string;
  value: number | null;
  risk: number | null;
  weight: number;
  available: boolean;
};

export type StudentRisk = {
  student_id: number;
  student_name: string | null;
  risk_score: number;
  band: RiskBand;
  attendance_pct: number | null;
  cgpa: number | null;
  submission_rate: number | null;
  reasons: string[];
  factors: RiskFactor[];
};

export type ClassAnalytics = {
  section_id: number;
  section_name: string | null;
  student_count: number;
  avg_attendance_pct: number | null;
  avg_cgpa: number | null;
  results_coverage: number;
  total_assignments: number;
  avg_submission_rate: number | null;
  risk_high: number;
  risk_medium: number;
  risk_low: number;
  at_risk_count: number;
};

export const BAND_STYLES: Record<RiskBand, string> = {
  high: "bg-red-100 text-red-800",
  medium: "bg-amber-100 text-amber-800",
  low: "bg-green-100 text-green-800",
};

export const BAND_BAR: Record<RiskBand, string> = {
  high: "bg-red-500",
  medium: "bg-amber-500",
  low: "bg-green-500",
};

// Format a maybe-missing number: "—" when null, else value + optional suffix.
export function fmt(value: number | null, suffix = ""): string {
  return value == null ? "—" : `${value}${suffix}`;
}

// Pick a bar color from a 0-100 risk value (matches the backend bands).
export function riskColor(risk: number): string {
  if (risk >= 60) return BAND_BAR.high;
  if (risk >= 35) return BAND_BAR.medium;
  return BAND_BAR.low;
}

export function getMe(): Promise<MeUser> {
  return api.get("/auth/me") as Promise<MeUser>;
}

export function listDepartments(): Promise<Department[]> {
  return api.get("/admin/departments") as Promise<Department[]>;
}

export function listSections(departmentId: number): Promise<Section[]> {
  return api.get(`/admin/departments/${departmentId}/sections`) as Promise<
    Section[]
  >;
}

export function sectionAnalytics(sectionId: number): Promise<ClassAnalytics> {
  return api.get(`/analytics/section/${sectionId}`) as Promise<ClassAnalytics>;
}

export function sectionAtRisk(
  sectionId: number,
  band?: RiskBand | null,
): Promise<StudentRisk[]> {
  const qs = band ? `?band=${band}` : "";
  return api.get(`/analytics/section/${sectionId}/at-risk${qs}`) as Promise<
    StudentRisk[]
  >;
}

export function myRisk(): Promise<StudentRisk> {
  return api.get("/analytics/me") as Promise<StudentRisk>;
}
