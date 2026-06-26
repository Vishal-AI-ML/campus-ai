/**
 * Shared types + helpers for the face-attendance UI (enrollment + photo match).
 *
 * Mirrors the backend Pydantic schemas exactly so the frontend stays in sync
 * with `/face/*` and `/attendance/*`. Place at: src/components/face/faceApi.ts
 */

export type Department = { id: number; name: string; code: string }

export type Section = {
	id: number
	name: string
	year: number | null
	department_id: number
}

/** One roster student + whether they have an enrolled reference face. */
export type EnrollmentStatus = {
	student_id: number
	full_name: string
	email: string
	enrolled: boolean
	det_score: number | null
	enrolled_at: string | null
}

/** Returned after a successful enroll. */
export type FaceEnrollmentOut = {
	student_id: number
	enrolled_by_id: number | null
	det_score: number | null
	enrolled_at: string
}

export type AttendanceStatusValue = "present" | "absent" | "late"

/** One roster student + whether the class photo matched them. */
export type MatchSuggestion = {
	student_id: number
	full_name: string
	enrolled: boolean
	matched: boolean
	score: number | null
	suggested_status: AttendanceStatusValue
}

/** An enrolled student matched in the photo but NOT in this section. */
export type MatchOutsider = { student_id: number; score: number }

export type PhotoMatchResponse = {
	section_id: number
	detected_faces: number
	unmatched_faces: number
	threshold: number
	suggestions: MatchSuggestion[]
	matched_outside_section: MatchOutsider[]
}

/**
 * Read an image File and return RAW base64 (without the `data:...;base64,`
 * prefix), which is what the backend / face worker expects.
 */
export async function fileToBase64(file: File): Promise<string> {
	const dataUrl = await new Promise<string>((resolve, reject) => {
		const reader = new FileReader()
		reader.onload = () => resolve(String(reader.result))
		reader.onerror = () => reject(new Error("Could not read the image file"))
		reader.readAsDataURL(file)
	})
	const comma = dataUrl.indexOf(",")
	return comma >= 0 ? dataUrl.slice(comma + 1) : dataUrl
}

/** Today's date as YYYY-MM-DD in the user's local timezone. */
export function todayLocal(): string {
	const now = new Date()
	const tzOffsetMs = now.getTimezoneOffset() * 60_000
	return new Date(now.getTime() - tzOffsetMs).toISOString().slice(0, 10)
}
