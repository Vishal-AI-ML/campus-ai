// Shared types + helpers for the Assignments UI.
// Mirrors the backend contracts exposed under /assignments and /admin.

export type SubmissionStatus = "submitted" | "graded"

export interface Department {
	id: number
	name: string
	code: string
}

export interface Section {
	id: number
	name: string
	year: number | null
	department_id: number
}

export interface AssignmentOut {
	id: number
	section_id: number
	subject_id: number | null
	title: string
	description: string | null
	due_date: string
	max_marks: number
	created_by_id: number | null
	created_at: string
}

// Student-facing list item: assignment + the viewer's own submission state.
export interface AssignmentWithStatus extends AssignmentOut {
	submitted: boolean
	submission_status: SubmissionStatus | null
	marks: number | null
}

export interface SubmissionOut {
	id: number
	assignment_id: number
	student_id: number
	content: string | null
	link: string | null
	status: SubmissionStatus
	marks: number | null
	feedback: string | null
	graded_by_id: number | null
	submitted_at: string
	graded_at: string | null
}

export interface MeUser {
	id: number
	email: string
	full_name: string
	role: string
	section_id?: number | null
}

// Render an ISO timestamp in the viewer's local timezone (best-effort).
export function formatDateTime(iso: string): string {
	try {
		return new Date(iso).toLocaleString()
	} catch {
		return iso
	}
}
