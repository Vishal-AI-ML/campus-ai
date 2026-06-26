"use client"

import { useEffect, useState } from "react"

import { api, ApiError } from "@/lib/api"

import { formatDateTime } from "./assignmentsApi"
import type { AssignmentWithStatus, SubmissionOut } from "./assignmentsApi"

// Student view: list this section's assignments, submit work, see grades.
export default function AssignmentStudentPanel() {
	const [items, setItems] = useState<AssignmentWithStatus[]>([])
	const [loading, setLoading] = useState(true)
	const [error, setError] = useState<string | null>(null)
	const [forms, setForms] = useState<
		Record<number, { content: string; link: string }>
	>({})
	const [savingId, setSavingId] = useState<number | null>(null)
	const [feedbacks, setFeedbacks] = useState<Record<number, SubmissionOut>>({})

	async function load() {
		setLoading(true)
		setError(null)
		try {
			const data = await api.get("/assignments/me")
			setItems(data as AssignmentWithStatus[])
		} catch (e) {
			setError(e instanceof ApiError ? e.message : "Failed to load assignments")
		} finally {
			setLoading(false)
		}
	}

	useEffect(() => {
		void load()
	}, [])

	async function handleSubmit(assignmentId: number) {
		const form = forms[assignmentId] ?? { content: "", link: "" }
		if (!form.content && !form.link) {
			setError("Add some text or a link before submitting")
			return
		}
		setSavingId(assignmentId)
		setError(null)
		try {
			await api.post(`/assignments/${assignmentId}/submit`, {
				content: form.content || null,
				link: form.link || null,
			})
			await load()
		} catch (e) {
			setError(e instanceof ApiError ? e.message : "Failed to submit")
		} finally {
			setSavingId(null)
		}
	}

	async function viewFeedback(assignmentId: number) {
		try {
			const data = await api.get(`/assignments/${assignmentId}/my-submission`)
			setFeedbacks((prev) => ({ ...prev, [assignmentId]: data as SubmissionOut }))
		} catch (e) {
			setError(e instanceof ApiError ? e.message : "Failed to load feedback")
		}
	}

	const gradedBadge =
		"rounded-full bg-emerald-500/15 px-2 py-0.5 text-xs text-emerald-400"
	const submittedBadge =
		"rounded-full bg-amber-500/15 px-2 py-0.5 text-xs text-amber-400"
	const pendingBadge =
		"rounded-full bg-white/10 px-2 py-0.5 text-xs text-white/60"

	if (loading) return <p className="text-sm text-white/60">Loading…</p>

	return (
		<div className="space-y-4">
			{error ? (
				<p className="rounded-md bg-red-500/10 px-3 py-2 text-sm text-red-400">
					{error}
				</p>
			) : null}

			{items.length === 0 ? (
				<p className="text-sm text-white/60">
					No assignments for your section yet.
				</p>
			) : (
				items.map((a) => {
					const form = forms[a.id] ?? { content: "", link: "" }
					const fb = feedbacks[a.id]
					const badgeClass =
						a.submission_status === "graded"
							? gradedBadge
							: a.submitted
								? submittedBadge
								: pendingBadge
					const badgeLabel =
						a.submission_status === "graded"
							? "graded"
							: a.submitted
								? "submitted"
								: "pending"
					return (
						<div
							key={a.id}
							className="rounded-lg border border-white/10 bg-white/5 p-4"
						>
							<div className="flex items-start justify-between gap-3">
								<div>
									<p className="font-medium text-white">{a.title}</p>
									{a.description ? (
										<p className="mt-1 text-sm text-white/60">{a.description}</p>
									) : null}
									<p className="mt-1 text-xs text-white/40">
										Due {formatDateTime(a.due_date)} · Max {a.max_marks}
									</p>
								</div>
								<span className={badgeClass}>{badgeLabel}</span>
							</div>

							{a.submission_status === "graded" ? (
								<div className="mt-3 rounded-md bg-emerald-500/10 p-3 text-sm text-emerald-300">
									Score: {a.marks} / {a.max_marks}
									{fb ? (
										fb.feedback ? (
											<p className="mt-1 text-emerald-200/80">📝 {fb.feedback}</p>
										) : (
											<p className="mt-1 text-emerald-200/60">
												No written feedback.
											</p>
										)
									) : (
										<button
											onClick={() => viewFeedback(a.id)}
											className="ml-2 text-xs underline"
										>
											View feedback
										</button>
									)}
								</div>
							) : (
								<div className="mt-3 space-y-2">
									<textarea
										value={form.content}
										onChange={(e) =>
											setForms((prev) => ({
												...prev,
												[a.id]: { ...form, content: e.target.value },
											}))
										}
										placeholder="Your answer / notes"
										rows={2}
										className="w-full rounded-md border border-white/10 bg-black/30 px-3 py-2 text-sm text-white"
									/>
									<input
										value={form.link}
										onChange={(e) =>
											setForms((prev) => ({
												...prev,
												[a.id]: { ...form, link: e.target.value },
											}))
										}
										placeholder="Link (Google Drive, GitHub, etc.)"
										className="w-full rounded-md border border-white/10 bg-black/30 px-3 py-2 text-sm text-white"
									/>
									<button
										onClick={() => handleSubmit(a.id)}
										disabled={savingId === a.id}
										className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
									>
										{savingId === a.id
											? "Submitting…"
											: a.submitted
												? "Re-submit"
												: "Submit"}
									</button>
								</div>
							)}
						</div>
					)
				})
			)}
		</div>
	)
}
