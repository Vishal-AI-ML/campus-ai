"use client"

/**
 * Class-photo attendance (teacher/admin): pick a section + date, upload a class
 * photo, and the AI worker suggests who is present. The teacher reviews/edits
 * the suggestions and confirms - only then is attendance actually written via
 * the existing POST /attendance/mark (human-in-the-loop, moat-safe).
 *
 * Place at: src/components/face/PhotoAttendancePanel.tsx
 */

import { useState } from "react"

import { api, ApiError } from "@/lib/api"

import SectionPicker from "./SectionPicker"
import { fileToBase64, todayLocal } from "./faceApi"
import type {
	AttendanceStatusValue,
	PhotoMatchResponse,
} from "./faceApi"

const STATUS_OPTIONS: AttendanceStatusValue[] = ["present", "absent", "late"]

export default function PhotoAttendancePanel() {
	const [sectionId, setSectionId] = useState<number | null>(null)
	const [date, setDate] = useState<string>(todayLocal())
	const [file, setFile] = useState<File | undefined>(undefined)
	const [result, setResult] = useState<PhotoMatchResponse | null>(null)
	const [statuses, setStatuses] = useState<Record<number, AttendanceStatusValue>>(
		{},
	)
	const [matching, setMatching] = useState(false)
	const [saving, setSaving] = useState(false)
	const [error, setError] = useState<string | null>(null)
	const [notice, setNotice] = useState<string | null>(null)

	async function runMatch() {
		if (sectionId === null) {
			setError("Pick a section first.")
			return
		}
		if (!file) {
			setError("Choose a class photo first.")
			return
		}
		setMatching(true)
		setError(null)
		setNotice(null)
		setResult(null)
		try {
			const image_base64 = await fileToBase64(file)
			const res = (await api.post("/attendance/photo", {
				section_id: sectionId,
				image_base64,
			})) as PhotoMatchResponse
			setResult(res)
			// Seed the editable statuses from the AI suggestions.
			const seeded: Record<number, AttendanceStatusValue> = {}
			for (const s of res.suggestions) seeded[s.student_id] = s.suggested_status
			setStatuses(seeded)
		} catch (e) {
			setError(
				e instanceof ApiError ? e.message : "Face matching failed. Try again.",
			)
		} finally {
			setMatching(false)
		}
	}

	async function confirmAndMark() {
		if (sectionId === null || !result) return
		setSaving(true)
		setError(null)
		setNotice(null)
		try {
			const records = result.suggestions.map((s) => ({
				student_id: s.student_id,
				status: statuses[s.student_id] ?? "absent",
			}))
			await api.post("/attendance/mark", {
				section_id: sectionId,
				date,
				records,
			})
			const presentCount = records.filter((r) => r.status !== "absent").length
			setNotice(
				`Attendance saved for ${date}: ${presentCount}/${records.length} marked present/late.`,
			)
		} catch (e) {
			setError(e instanceof ApiError ? e.message : "Could not save attendance")
		} finally {
			setSaving(false)
		}
	}

	return (
		<div className="space-y-4">
			<div className="space-y-3 rounded-lg border border-gray-200 dark:border-white/10 bg-white dark:bg-slate-900 p-4">
				<SectionPicker
					onSectionChange={(id) => {
						setSectionId(id)
						setResult(null)
						setNotice(null)
					}}
				/>
				<div className="flex flex-wrap items-end gap-3">
					<label className="flex flex-col gap-1 text-sm">
						<span className="font-medium text-gray-700 dark:text-slate-300">Date</span>
						<input
							type="date"
							value={date}
							onChange={(e) => setDate(e.target.value)}
							className="rounded-md border border-gray-300 dark:border-white/15 px-3 py-2 text-sm"
						/>
					</label>
					<label className="flex flex-col gap-1 text-sm">
						<span className="font-medium text-gray-700 dark:text-slate-300">Class photo</span>
						<input
							type="file"
							accept="image/*"
							onChange={(e) => setFile(e.target.files?.[0])}
							className="text-sm"
						/>
					</label>
					<button
						type="button"
						disabled={matching || sectionId === null || !file}
						onClick={runMatch}
						className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
					>
						{matching ? "Matching faces..." : "Match faces"}
					</button>
				</div>
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

			{result && (
				<div className="space-y-3 rounded-lg border border-gray-200 dark:border-white/10 bg-white dark:bg-slate-900 p-4">
					<div className="flex flex-wrap gap-4 text-sm text-gray-600 dark:text-slate-300">
						<span>
							Faces detected:{" "}
							<strong className="text-gray-900 dark:text-slate-100">{result.detected_faces}</strong>
						</span>
						<span>
							Unmatched faces:{" "}
							<strong className="text-gray-900 dark:text-slate-100">{result.unmatched_faces}</strong>
						</span>
						<span>
							Threshold:{" "}
							<strong className="text-gray-900 dark:text-slate-100">{result.threshold}</strong>
						</span>
					</div>

					{result.matched_outside_section.length > 0 && (
						<p className="rounded-md bg-amber-50 px-3 py-2 text-xs text-amber-700">
							Heads up: {result.matched_outside_section.length} enrolled
							student(s) from another section were detected in this photo and
							were ignored here.
						</p>
					)}

					<ul className="divide-y divide-gray-100 dark:divide-white/10">
						{result.suggestions.map((s) => (
							<li
								key={s.student_id}
								className="flex flex-wrap items-center gap-3 py-3"
							>
								<div className="min-w-[180px] flex-1">
									<p className="text-sm font-medium text-gray-900 dark:text-slate-100">
										{s.full_name}
									</p>
									<p className="text-xs text-gray-500 dark:text-slate-400">
										{!s.enrolled
											? "Not enrolled - cannot be auto-matched"
											: s.matched
												? `Matched - score ${s.score?.toFixed(2) ?? ""}`
												: "No match in this photo"}
									</p>
								</div>

								{s.matched && (
									<span className="rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">
										AI: present
									</span>
								)}

								<select
									value={statuses[s.student_id] ?? "absent"}
									onChange={(e) =>
										setStatuses((prev) => ({
											...prev,
											[s.student_id]: e.target
												.value as AttendanceStatusValue,
										}))
									}
									className="rounded-md border border-gray-300 dark:border-white/15 px-2 py-1 text-sm capitalize"
								>
									{STATUS_OPTIONS.map((opt) => (
										<option key={opt} value={opt} className="capitalize">
											{opt}
										</option>
									))}
								</select>
							</li>
						))}
					</ul>

					<div className="flex items-center justify-end gap-3 border-t border-gray-100 dark:border-white/10 pt-3">
						<p className="text-xs text-gray-400 dark:text-slate-500">
							Review the suggestions, then confirm to write attendance.
						</p>
						<button
							type="button"
							disabled={saving}
							onClick={confirmAndMark}
							className="rounded-md bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
						>
							{saving ? "Saving..." : "Confirm & mark attendance"}
						</button>
					</div>
				</div>
			)}
		</div>
	)
}
