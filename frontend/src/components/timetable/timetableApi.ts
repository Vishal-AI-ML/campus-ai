// Typed API helpers + shared types for the Timetable module.
// Mirrors the backend `/timetable` routes (weekly recurring class schedule).
import { api } from "@/lib/api"

export type Role = "student" | "teacher" | "tpo" | "admin"

export type MeUser = {
  id: number
  email: string
  full_name: string
  role: Role
  section_id: number | null
}

export type Department = { id: number; name: string; code: string }
export type Section = {
  id: number
  name: string
  year: number | null
  department_id: number
}

export type TimetableEntry = {
  id: number
  section_id: number
  section_name: string | null
  subject_id: number | null
  subject_name: string | null
  teacher_id: number | null
  teacher_name: string | null
  day_of_week: number
  start_time: string
  end_time: string
  room: string | null
}

export type TimetableCreate = {
  section_id: number
  day_of_week: number
  start_time: string
  end_time: string
  room?: string | null
  subject_id?: number | null
  teacher_id?: number | null
}

// 0=Monday .. 6=Sunday (matches the backend `day_of_week`).
export const DAYS = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
]

// "09:00:00" -> "09:00"
export function formatTime(t: string): string {
  if (!t) return ""
  return t.slice(0, 5)
}

export function getMe(): Promise<MeUser> {
  return api.get("/auth/me") as Promise<MeUser>
}

export function listDepartments(): Promise<Department[]> {
  return api.get("/admin/departments") as Promise<Department[]>
}

export function listSections(departmentId: number): Promise<Section[]> {
  return api.get(`/admin/departments/${departmentId}/sections`) as Promise<
    Section[]
  >
}

export function listSectionTimetable(
  sectionId: number
): Promise<TimetableEntry[]> {
  return api.get(`/timetable?section_id=${sectionId}`) as Promise<
    TimetableEntry[]
  >
}

export function myTimetable(): Promise<TimetableEntry[]> {
  return api.get("/timetable/me") as Promise<TimetableEntry[]>
}

export function myTeaching(): Promise<TimetableEntry[]> {
  return api.get("/timetable/teaching") as Promise<TimetableEntry[]>
}

export function createEntry(
  payload: TimetableCreate
): Promise<TimetableEntry> {
  return api.post("/timetable", payload) as Promise<TimetableEntry>
}

export function deleteEntry(id: number): Promise<void> {
  return api.delete(`/timetable/${id}`) as Promise<void>
}
