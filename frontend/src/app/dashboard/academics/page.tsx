/**
 * Campus AI - Student Academics page.
 *
 * Place this file at: src/app/dashboard/academics/page.tsx
 *
 * Shows the student's CGPA, per-semester SGPA, and a subject-wise results
 * breakdown. CGPA/SGPA are credit-weighted averages of 10-point grade points
 * (computed by the backend).
 *
 * Backend endpoints:
 *   GET /academics/me/summary -> { cgpa, total_credits, semesters: [{ semester, sgpa, credits }] }
 *   GET /academics/me/results -> [{ id, student_id, subject_id, marks_obtained, max_marks, grade_point }]
 *   GET /academics/subjects   -> [{ id, name, code, credits, semester, department_id }]  (used to label results)
 */

"use client"

import { useEffect, useState } from "react"
import { api, ApiError } from "@/lib/api"

type SemesterGPA = {
	semester: number
	sgpa: number
	credits: number
}

type Summary = {
	cgpa: number
	total_credits: number
	semesters: SemesterGPA[]
}

type ResultItem = {
	id: number
	student_id: number
	subject_id: number
	marks_obtained: number
	max_marks: number
	grade_point: number
}

type Subject = {
	id: number
	name: string
	code: string
	credits: number
	semester: number
	department_id: number
}

function gpaColor(value: number): string {
	if (value >= 8) return "text-emerald-400"
	if (value >= 6.5) return "text-amber-400"
	return "text-red-400"
}

export default function AcademicsPage() {
	const [summary, setSummary] = useState<Summary | null>(null)
	const [results, setResults] = useState<ResultItem[]>([])
	const [subjects, setSubjects] = useState<Subject[]>([])
	const [loading, setLoading] = useState(true)
	const [error, setError] = useState<string | null>(null)

	useEffect(() => {
		async function load() {
			setLoading(true)
			setError(null)
			try {
				const [s, r, subs] = await Promise.all([
					api.get<Summary>("/academics/me/summary"),
					api.get<ResultItem[]>("/academics/me/results"),
					api.get<Subject[]>("/academics/subjects"),
				])
				setSummary(s)
				setResults(r)
				setSubjects(subs)
			} catch (err) {
				setError(
					err instanceof ApiError
						? err.message
						: "Could not load academics.",
				)
			} finally {
				setLoading(false)
			}
		}
		load()
	}, [])

	// Lookup map so each result row can show its subject name + code.
	const subjectById: Record<number, Subject> = {}
	for (const subject of subjects) {
		subjectById[subject.id] = subject
	}

	return (
		<div>
			<h2 className="text-2xl font-bold">My Academics</h2>
			<p className="mt-1 text-sm text-slate-400">
				Your CGPA, per-semester SGPA, and subject results.
			</p>

			{error && (
				<p className="mt-4 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">
					{error}
				</p>
			)}

			{loading ? (
				<p className="mt-6 text-slate-400">Loading your academics...</p>
			) : summary && summary.total_credits === 0 ? (
				<p className="mt-6 text-slate-400">No results published yet.</p>
			) : (
				summary && (
					<>
						{/* CGPA + per-semester SGPA */}
						<div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
							<div className="rounded-2xl border border-indigo-400/30 bg-indigo-500/10 p-6">
								<p className="text-sm text-slate-300">CGPA</p>
								<p
									className={`mt-1 text-4xl font-bold ${gpaColor(
										summary.cgpa,
									)}`}
								>
									{summary.cgpa.toFixed(2)}
								</p>
								<p className="mt-1 text-xs text-slate-400">
									{summary.total_credits} total credits
								</p>
							</div>
							{summary.semesters.map((sem) => (
								<div
									key={sem.semester}
									className="rounded-2xl border border-white/10 bg-white/5 p-6"
								>
									<p className="text-sm text-slate-400">
										Semester {sem.semester}
									</p>
									<p
										className={`mt-1 text-4xl font-bold ${gpaColor(
											sem.sgpa,
										)}`}
									>
										{sem.sgpa.toFixed(2)}
									</p>
									<p className="mt-1 text-xs text-slate-500">
										{sem.credits} credits
									</p>
								</div>
							))}
						</div>

						{/* Subject-wise results */}
						<div className="mt-8">
							<h3 className="text-lg font-semibold">Subject results</h3>
							<div className="mt-3 space-y-2">
								{results.map((result) => {
									const subject = subjectById[result.subject_id]
									const percentage = Math.round(
										(result.marks_obtained / result.max_marks) * 100,
									)
									return (
										<div
											key={result.id}
											className="flex items-center justify-between rounded-xl border border-white/10 bg-white/5 px-4 py-3"
										>
											<div>
												<p className="text-sm font-medium text-slate-200">
													{subject
														? `${subject.name} (${subject.code})`
														: `Subject #${result.subject_id}`}
												</p>
												<p className="mt-0.5 text-xs text-slate-500">
													{subject
														? `Sem ${subject.semester} \u00b7 ${subject.credits} credits`
														: ""}
												</p>
											</div>
											<div className="text-right">
												<p className="text-sm text-slate-300">
													{result.marks_obtained}/{result.max_marks}{" "}
													<span className="text-slate-500">
														({percentage}%)
													</span>
												</p>
												<p
													className={`text-xs font-semibold ${gpaColor(
													result.grade_point,
												)}`}
												>
													GP {result.grade_point.toFixed(1)}
												</p>
											</div>
										</div>
									)
								})}
							</div>
						</div>
					</>
				)
			)}
		</div>
	)
}
