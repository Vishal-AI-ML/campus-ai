"use client"

import { useState, type FormEvent } from "react"

import { api, ApiError } from "@/lib/api"

import SectionPicker from "./SectionPicker"
import { formatDateTime } from "./assignmentsApi"
import type { AssignmentOut, Section, SubmissionOut } from "./assignmentsApi"

// Teacher / admin view: create assignments for a section and grade submissions.
export default function AssignmentTeacherPanel() {
	const [section, setSection] = useState<Section | null>(null)
	const [assignments, setAssignments] = useState<AssignmentOut[]>([])
	const [loadingList, setLoadingList] = useState(false)
	const [error, setError] = useState<string | null>(null)

	// New-assignment form fields.
	const [title, setTitle] = useState("")
	const [description, setDescription] = useState("")
	const [dueDate, setDueDate] = useState("")
	const [maxMarks, setMaxMarks] = useState("100")
	const [creating, setCreating] = useState(false)

	// Inline submissions + grading state for the expanded assignment.
	const [openId, setOpenId] = useState<number | null>(null)
	const [submissions, setSubmissions] = useState<SubmissionOut[]>([])
	const [loadingSubs, setLoadingSubs] = useState(false)
	const [gradeInputs, setGradeInputs] = useState<
		Record<number, { marks: string; feedback: string }>
	>({})
	const [gradingId, setGradingId] = useState<number | null>(null)

	async function loadAssignments(sectionId: number) {
		setLoadingList(true)
		setError(null)
		try {
			const data = await api.get(`/assignments?section_id=${sectionId}`)
			setAssignments(data as AssignmentOut[])
		} catch (e) {
			setError(e instanceof ApiError ? e.message : "Failed to load assignments")
		} finally {
			setLoadingList(false)
		}
	}

	function handleSection(sectionId: number | null, sec: Section | null) {
		setSection(sec)
		setOpenId(null)
		setSubmissions([])
		if (sectionId !== null) {
			void loadAssignments(sectionId)
		} else {
			setAssignments([])
		}
	}

	async function handleCreate(e: FormEvent) {
		e.preventDefault()
		if (!section) return
		setCreating(true)
		setError(null)
		try {
			await api.post("/assignments", {
				section_id: section.id,
				title,
				description: description || null,
				due_date: new Date(dueDate).toISOString(),
				max_marks: parseFloat(maxMarks) || 0,
			})
			setTitle("")
			setDescription("")
			setDueDate("")
			setMaxMarks("100")
			await loadAssignments(section.id)
		} catch (err) {
			setError(
				err instanceof ApiError ? err.message : "Failed to create assignment",
			)
		} finally {
			setCreating(false)
		}
	}

	async function reloadSubmissions(assignmentId: number) {
		setLoadingSubs(true)
		setError(null)
		try {
			const data = await api.get(`/assignments/${assignmentId}/submissions`)
			const subs = data as SubmissionOut[]
			setSubmissions(subs)
			const inputs: Record<number, { marks: string; feedback: string }> = {}
			subs.forEach((s) => {
				inputs[s.id] = {
					marks: s.marks != null ? String(s.marks) : "",
					feedback: s.feedback ?? "",
				}
			})
			setGradeInputs(inputs)
		} catch (e) {
			setError(e instanceof ApiError ? e.message : "Failed to load submissions")
		} finally {
			setLoadingSubs(false)
		}
	}

	function toggleSubmissions(assignmentId: number) {
		if (openId === assignmentId) {
			setOpenId(null)
			setSubmissions([])
			return
		}
		setOpenId(assignmentId)
		void reloadSubmissions(assignmentId)
	}

	async function handleGrade(submissionId: number) {
		const input = gradeInputs[submissionId]
		if (!input) return
		setGradingId(submissionId)
		setError(null)
		try {
			await api.patch(`/assignments/submissions/${submissionId}/grade`, {
				marks: parseFloat(input.marks) || 0,
				feedback: input.feedback || null,
			})
			if (openId !== null) await reloadSubmissions(openId)
		} catch (e) {
			setError(e instanceof ApiError ? e.message : "Failed to save grade")
		} finally {
			setGradingId(null)
		}
	}

	const gradedBadge =
		"rounded-full bg-emerald-500/15 px-2 py-0.5 text-xs text-emerald-600 dark:text-emerald-300"
	const pendingBadge =
		"rounded-full bg-amber-500/15 px-2 py-0.5 text-xs text-amber-400"

	return (
		<div className="space-y-6">
			<SectionPicker onSectionChange={handleSection} />

			{error ? (
				<p className="rounded-md bg-red-500/10 px-3 py-2 text-sm text-red-400">
					{error}
				</p>
			) : null}

			{section ? (
				<>
					<form
						onSubmit={handleCreate}
						className="space-y-3 rounded-lg border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-900 p-4"
					>
						<h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
							➕ New assignment for {section.name}
						</h3>
						<input
							value={title}
							onChange={(e) => setTitle(e.target.value)}
							placeholder="Title (e.g. DBMS Lab 1)"
							required
							className="w-full rounded-md border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-900 px-3 py-2 text-sm text-slate-900 dark:text-slate-100"
						/>
						<textarea
							value={description}
							onChange={(e) => setDescription(e.target.value)}
							placeholder="Description / instructions (optional)"
							rows={3}
							className="w-full rounded-md border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-900 px-3 py-2 text-sm text-slate-900 dark:text-slate-100"
						/>
						<div className="flex flex-wrap gap-3">
							<label className="flex flex-col text-xs text-slate-500 dark:text-slate-400">
								Due date
								<input
									type="datetime-local"
									value={dueDate}
									onChange={(e) => setDueDate(e.target.value)}
									required
									className="mt-1 rounded-md border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-900 px-3 py-2 text-sm text-slate-900 dark:text-slate-100"
								/>
							</label>
							<label className="flex flex-col text-xs text-slate-500 dark:text-slate-400">
								Max marks
								<input
									type="number"
									min="1"
									value={maxMarks}
									onChange={(e) => setMaxMarks(e.target.value)}
									required
									className="mt-1 w-28 rounded-md border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-900 px-3 py-2 text-sm text-slate-900 dark:text-slate-100"
								/>
							</label>
						</div>
						<button
							type="submit"
							disabled={creating}
							className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
						>
							{creating ? "Creating…" : "Create assignment"}
						</button>
					</form>

					<div className="space-y-3">
						<h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">📋 Assignments</h3>
						{loadingList ? (
							<p className="text-sm text-slate-500 dark:text-slate-400">Loading…</p>
						) : assignments.length === 0 ? (
							<p className="text-sm text-slate-500 dark:text-slate-400">
								No assignments yet for this section.
							</p>
						) : (
							assignments.map((a) => (
								<div
									key={a.id}
								className="rounded-lg border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-900 p-4"
								>
									<div className="flex items-start justify-between gap-3">
										<div>
											<p className="font-medium text-slate-900 dark:text-slate-100">{a.title}</p>
											{a.description ? (
												<p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
													{a.description}
												</p>
											) : null}
											<p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
												Due {formatDateTime(a.due_date)} · Max {a.max_marks}
											</p>
										</div>
										<button
											onClick={() => toggleSubmissions(a.id)}
											className="shrink-0 rounded-md border border-slate-300 dark:border-white/15 px-3 py-1.5 text-xs text-slate-900 dark:text-slate-100 hover:bg-slate-100 dark:hover:bg-white/10"
										>
											{openId === a.id ? "Hide submissions" : "View submissions"}
										</button>
									</div>

									{openId === a.id ? (
										<div className="mt-4 space-y-3 border-t border-slate-200 dark:border-white/10 pt-4">
											{loadingSubs ? (
												<p className="text-sm text-slate-500 dark:text-slate-400">
													Loading submissions…
												</p>
											) : submissions.length === 0 ? (
												<p className="text-sm text-slate-500 dark:text-slate-400">No submissions yet.</p>
											) : (
												submissions.map((s) => {
													const input =
														gradeInputs[s.id] ?? { marks: "", feedback: "" }
													return (
														<div key={s.id} className="rounded-md bg-black/20 p-3">
															<div className="flex items-center justify-between">
																<p className="text-sm text-slate-900 dark:text-slate-100">
																	Student #{s.student_id}
																</p>
																<span
																	className={
																		s.status === "graded" ? gradedBadge : pendingBadge
																	}
																>
																	{s.status}
																</span>
															</div>
															{s.content ? (
																<p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
																	{s.content}
																</p>
															) : null}
															{s.link ? (
																<a
																	href={s.link}
																	target="_blank"
																	rel="noreferrer"
																	className="mt-1 inline-block text-xs text-indigo-400 underline"
																>
																	🔗 Open link
																</a>
															) : null}
															<div className="mt-3 flex flex-wrap items-end gap-2">
																<label className="flex flex-col text-xs text-slate-500 dark:text-slate-400">
																	Marks (max {a.max_marks})
																	<input
																		type="number"
																		min="0"
																		max={a.max_marks}
																		value={input.marks}
																		onChange={(e) =>
																			setGradeInputs((prev) => ({
																				...prev,
																				[s.id]: { ...input, marks: e.target.value },
																			}))
																		}
																		className="mt-1 w-24 rounded-md border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-900 px-2 py-1 text-sm text-slate-900 dark:text-slate-100"
																	/>
																</label>
																<input
																	value={input.feedback}
																	onChange={(e) =>
																		setGradeInputs((prev) => ({
																			...prev,
																			[s.id]: { ...input, feedback: e.target.value },
																		}))
																	}
																	placeholder="Feedback (optional)"
																	className="mt-1 flex-1 rounded-md border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-900 px-2 py-1 text-sm text-slate-900 dark:text-slate-100"
																/>
																<button
																	onClick={() => handleGrade(s.id)}
																	disabled={gradingId === s.id}
																	className="rounded-md bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
																>
																	{gradingId === s.id ? "Saving…" : "Save grade"}
																</button>
															</div>
														</div>
													)
												})
											)}
										</div>
									) : null}
								</div>
							))
						)}
					</div>
				</>
			) : (
				<p className="text-sm text-slate-500 dark:text-slate-400">
					Pick a department and section to manage assignments.
				</p>
			)}
		</div>
	)
}
