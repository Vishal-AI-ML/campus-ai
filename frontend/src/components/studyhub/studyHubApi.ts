// Study Hub client-side types + small helpers.
// Mirrors the backend `/materials` responses and the `/admin` structure reads
// used by the section picker. Imported by the Study Hub panels + page.

export type MaterialCategory = "notes" | "slides" | "video" | "link" | "other"

export type Department = { id: number; name: string; code: string }

export type Section = {
	id: number
	name: string
	year: number | null
	department_id: number
}

export type MaterialOut = {
	id: number
	section_id: number
	subject_id: number | null
	title: string
	description: string | null
	content: string | null
	link: string | null
	category: MaterialCategory
	uploaded_by_id: number | null
	created_at: string
}

export type MeUser = {
	id: number
	email: string
	full_name: string
	role: string
	section_id?: number | null
}

// Ordered list for the upload form's category dropdown.
export const MATERIAL_CATEGORIES: MaterialCategory[] = [
	"notes",
	"slides",
	"video",
	"link",
	"other",
]

// Friendly label (with an emoji) for each category.
export const CATEGORY_LABEL: { [k in MaterialCategory]: string } = {
	notes: "\uD83D\uDCDD Notes",
	slides: "\uD83D\uDCCA Slides",
	video: "\uD83C\uDFAC Video",
	link: "\uD83D\uDD17 Link",
	other: "\uD83D\uDCCE Other",
}

// Render an ISO timestamp in the viewer's local time (best-effort).
export function formatDateTime(iso: string): string {
	try {
		return new Date(iso).toLocaleString()
	} catch {
		return iso
	}
}
