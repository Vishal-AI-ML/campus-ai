// Typed API helpers + shared types for the Leave / OD module.
// Mirrors the backend `/leave` routes (personal leave + official on-duty).
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

export type RequestType = "leave" | "od";
export type LeaveStatus = "pending" | "approved" | "rejected" | "cancelled";

export type LeaveRequest = {
  id: number;
  request_type: RequestType;
  category: string;
  student_id: number;
  student_name: string | null;
  section_id: number | null;
  section_name: string | null;
  title: string;
  reason: string | null;
  event_name: string | null;
  proof_url: string | null;
  start_date: string;
  end_date: string;
  status: LeaveStatus;
  applied_by_id: number | null;
  reviewed_by_id: number | null;
  reviewer_name: string | null;
  review_note: string | null;
  reviewed_at: string | null;
  bulk_group_id: string | null;
  days: number;
  created_at: string;
};

export type LeaveCreate = {
  request_type: RequestType;
  category: string;
  title: string;
  reason?: string | null;
  event_name?: string | null;
  proof_url?: string | null;
  start_date: string;
  end_date: string;
};

export type BulkODCreate = {
  student_ids: number[];
  category: string;
  title: string;
  event_name?: string | null;
  reason?: string | null;
  proof_url?: string | null;
  start_date: string;
  end_date: string;
};

export type BulkODResult = {
  bulk_group_id: string;
  created: number;
  skipped: number[];
  entries: LeaveRequest[];
};

// Categories allowed per type (must match the backend validation sets).
export const LEAVE_CATEGORIES = ["medical", "personal", "emergency"];
export const OD_CATEGORIES = [
  "fest",
  "technical",
  "sports",
  "competition",
  "ncc_nss",
  "industrial_visit",
  "placement",
  "other",
];

export const STATUS_STYLES: Record<LeaveStatus, string> = {
  pending: "bg-amber-100 text-amber-800",
  approved: "bg-green-100 text-green-800",
  rejected: "bg-red-100 text-red-800",
  cancelled: "bg-gray-100 dark:bg-slate-800 text-gray-600 dark:text-slate-300",
};

// Pretty-print a category like "ncc_nss" -> "Ncc Nss".
export function prettyCategory(c: string): string {
  return c
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
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

export function applyLeave(payload: LeaveCreate): Promise<LeaveRequest> {
  return api.post("/leave", payload) as Promise<LeaveRequest>;
}

export function myRequests(): Promise<LeaveRequest[]> {
  return api.get("/leave/me") as Promise<LeaveRequest[]>;
}

export function listRequests(params: {
  sectionId?: number | null;
  status?: LeaveStatus | null;
  requestType?: RequestType | null;
}): Promise<LeaveRequest[]> {
  const q = new URLSearchParams();
  if (params.sectionId != null) q.set("section_id", String(params.sectionId));
  if (params.status) q.set("status_filter", params.status);
  if (params.requestType) q.set("request_type", params.requestType);
  const qs = q.toString();
  return api.get(`/leave${qs ? `?${qs}` : ""}`) as Promise<LeaveRequest[]>;
}

export function decideRequest(
  id: number,
  status: "approved" | "rejected",
  reviewNote?: string,
): Promise<LeaveRequest> {
  return api.patch(`/leave/${id}/decision`, {
    status,
    review_note: reviewNote || null,
  }) as Promise<LeaveRequest>;
}

export function cancelRequest(id: number): Promise<LeaveRequest> {
  return api.post(`/leave/${id}/cancel`) as Promise<LeaveRequest>;
}

export function deleteRequest(id: number): Promise<void> {
  return api.delete(`/leave/${id}`) as Promise<void>;
}

export function createBulkOD(payload: BulkODCreate): Promise<BulkODResult> {
  return api.post("/leave/bulk-od", payload) as Promise<BulkODResult>;
}
