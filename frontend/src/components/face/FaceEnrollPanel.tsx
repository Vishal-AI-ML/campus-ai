"use client"

/**
 * Face Enrollment roster (teacher/admin): pick a section, see each student's
 * enrollment status, upload a single-face reference photo to enroll, or remove
 * an existing enrollment.
 *
 * Place at: src/components/face/FaceEnrollPanel.tsx
 */

import { useState } from "react"

import { api, ApiError } from "@/lib/api"

import SectionPicker from "./SectionPicker"
import { fileToBase64 } from "./faceApi"
import type { EnrollmentStatus, FaceEnrollmentOut } from "./faceApi"

export default function FaceEnrollPanel() {
	const [sectionId, setSectionId] = useState<number | null>(null)
	const [roster, setRoster] = useState<EnrollmentStatus[]>([])
	const [files, setFiles] = useState<Record<number, File | undefined>>({})
	const [busyId, setBusyId] = useState<number | null>(null)
	const [loading, setLoading] = useState(false)
	const [error, setError] = useState<string | null>(null)
	const [notice, setNotice] = useState<string | null>(null)

	async function loadRoster(id: number | null) {
		setSectionId(id)
		setRoster([])
		setFiles({})
		setError(null)
		setNotice(null)
		if (id === null) return
		setLoading(true)
		try {
			const data = (await api.get(
				`/face/enrollments?section_id=${id}`,
			)) as EnrollmentStatus[]
			setRoster(data)
		} catch (e) {
			setError(e instanceof ApiError ? e.message : "Could not load the roster")
		} finally {
			setLoading(false)
		}
	}

	async function enroll(studentId: number) {
		const file = files[studentId]
		if (!file) {
			setError("Pick a photo for this student first.")
			return
		}
		setBusyId(studentId)
		setError(null)
		setNotice(null)
		try {
			const image_base64 = await fileToBase64(file)
			const res = (await api.post("/face/enroll", {
				student_id: studentId,
				image_base64,
			})) as FaceEnrollmentOut
			setNotice(
				`Enrolled student #${studentId} (face quality ${
					res.det_score?.toFixed(2) ?? "n/a"
				}).`,
			)
			await loadRoster(sectionId)
		} catch (e) {
			// 422 here usually means 0 or >1 faces in the photo.
			setError(
				e instanceof ApiError
					? e.message
					: "Enrollment failed. Use a clear photo with exactly one face.",
			)
		} finally {
			setBusyId(null)
		}
	}

	async function remove(studentId: number) {
		setBusyId(studentId)
		setError(null)
		setNotice(null)
		try {
			await api.delete(`/face/enroll/${studentId}`)
			setNotice(`Removed enrollment for student #${studentId}.`)
			await loadRoster(sectionId)
		} catch (e) {
			setError(e instanceof ApiError ? e.message : "Could not remove enrollment")
		} finally {
			setBusyId(null)
		}
	}

	const enrolledCount = roster.filter((r) => r.enrolled).length

	return (
		<div className="space-y-4">
			<div className="rounded-lg border border-gray-200 bg-white p-4">
				<SectionPicker onSectionChange={(id) => loadRoster(id)} />
			</div>

			{notice && (
				<p className="rounded-md bg-green-50 px-3 py-2 text-sm text-green-700">
					{notice}
				</p>
			)}
			{error && (
				<p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
					{error}
				</p>
			)}

			{loading && <p className="text-sm text-gray-500">Loading roster...</p>}

			{sectionId !== null && !loading && roster.length === 0 && (
				<p className="text-sm text-gray-500">
					No students are assigned to this section yet.
				</p>
			)}

			{roster.length > 0 && (
				<div className="rounded-lg border border-gray-200 bg-white">
					<div className="flex items-center justify-between border-b border-gray-100 px-4 py-3">
						<h3 className="text-sm font-semibold text-gray-800">
							Enrollment roster
						</h3>
						<span className="text-sm text-gray-500">
							{enrolledCount} / {roster.length} enrolled
						</span>
					</div>
					<ul className="divide-y divide-gray-100">
						{roster.map((s) => (
							<li
								key={s.student_id}
							className="flex flex-wrap items-center gap-3 px-4 py-3"
						>
								<div className="min-w-[180px] flex-1">
									<p className="text-sm font-medium text-gray-900">
										{s.full_name}
									</p>
									<p className="text-xs text-gray-500">{s.email}</p>
								</div>

								{s.enrolled ? (
									<span className="rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">
										Enrolled
										{s.det_score != null
											? ` - q ${s.det_score.toFixed(2)}`
											: ""}
									</span>
								) : (
									<span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">
										Not enrolled
									</span>
								)}

								<input
									type="file"
									accept="image/*"
									className="text-xs"
									onChange={(e) =>
										setFiles((prev) => ({
											...prev,
											[s.student_id]: e.target.files?.[0],
										}))
									}
								/>

								<button
									type="button"
									disabled={busyId === s.student_id || !files[s.student_id]}
									onClick={() => enroll(s.student_id)}
									className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
								>
									{busyId === s.student_id
										? "Working..."
										: s.enrolled
											? "Re-enroll"
											: "Enroll"}
								</button>

								{s.enrolled && (
									<button
										type="button"
										disabled={busyId === s.student_id}
										onClick={() => remove(s.student_id)}
										className="rounded-md border border-red-200 px-3 py-1.5 text-sm font-medium text-red-600 hover:bg-red-50 disabled:opacity-50"
									>
										Remove
									</button>
								)}
							</li>
						))}
					</ul>
				</div>
			)}

			<p className="text-xs text-gray-400">
				Tip: use a clear, well-lit photo with exactly one face. The face
				embedding is stored in Qdrant; only a small status record is kept in
				the app database.
			</p>
		</div>
	)
}
