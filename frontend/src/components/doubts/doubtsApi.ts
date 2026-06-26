// Doubt Forum client-side types + helper. Mirrors the backend /doubts responses
// and the /admin structure reads used by the teacher's section picker.

export type DoubtStatus = "open" | "resolved"

export type Department = { id: number; name: string; code: string }

export type Section = {
	id: number
	name: string
	year: number | null
	department_id: number
}

export type AnswerOut = {
	id: number
	doubt_id: number
	body: string
	answered_by_id: number | null
	is_accepted: boolean
	upvote_count: number
	viewer_has_upvoted: boolean
	created_at: string
}

export type DoubtOut = {
	id: number
	section_id: number
	subject_id: number | null
	title: string
	body: string
	status: DoubtStatus
	asked_by_id: number | null
	answer_count: number
	created_at: string
	resolved_at: string | null
}

export type DoubtDetailOut = DoubtOut & { answers: AnswerOut[] }

export type MeUser = {
	id: number
	email: string
	full_name: string
	role: string
	section_id?: number | null
}

// Render an ISO timestamp in the viewer's local time (best-effort).
export function formatDateTime(iso: string): string {
	try {
		return new Date(iso).toLocaleString()
	} catch {
		return iso
	}
}
