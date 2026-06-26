"use client"

// Student doubt-forum panel: ask a doubt (auto-scoped to your own section) and
// browse your section's feed; open one to view/answer/upvote/accept.

import { useCallback, useEffect, useState, type FormEvent } from "react"
import { api, ApiError } from "@/lib/api"
import DoubtDetail from "./DoubtDetail"
import { formatDateTime, type DoubtOut, type MeUser } from "./doubtsApi"

export default function DoubtStudentPanel({ me }: { me: MeUser }) {
	const [doubts, setDoubts] = useState<DoubtOut[]>([])
	const [loading, setLoading] = useState(true)
	const [error, setError] = useState<string | null>(null)
	const [selected, setSelected] = useState<number | null>(null)

	const [title, setTitle] = useState("")
	const [body, setBody] = useState("")
	const [submitting, setSubmitting] = useState(false)
	const [formError, setFormError] = useState<string | null>(null)

	const load = useCallback(() => {
		setLoading(true)
		setError(null)
		api
			.get("/doubts/me")
			.then((data) => setDoubts(data as DoubtOut[]))
			.catch((e) =>
				setError(e instanceof ApiError ? e.message : "Failed to load doubts")
			)
			.finally(() => setLoading(false))
	}, [])

	useEffect(() => {
		load()
	}, [load])

	async function ask(e: FormEvent) {
		e.preventDefault()
		if (me.section_id == null) {
			setFormError("You are not assigned to a section yet")
			return
		}
		if (!title.trim() || !body.trim()) return
		setSubmitting(true)
		setFormError(null)
		try {
			await api.post("/doubts", {
				section_id: me.section_id,
				title: title.trim(),
				body: body.trim(),
			})
			setTitle("")
			setBody("")
			load()
		} catch (e) {
			setFormError(e instanceof ApiError ? e.message : "Failed to post doubt")
		} finally {
			setSubmitting(false)
		}
	}

	const statusBadge = (resolved: boolean) =>
		resolved
			? "shrink-0 rounded-full bg-green-100 px-2 py-0.5 text-xs text-green-700"
			: "shrink-0 rounded-full bg-amber-100 px-2 py-0.5 text-xs text-amber-700"

	if (selected !== null) {
		return (
			<DoubtDetail
				doubtId={selected}
				me={me}
				onBack={() => {
					setSelected(null)
					load()
				}}
				onChanged={load}
			/>
		)
	}

	return (
		<div className="space-y-6">
			{me.section_id == null ? (
				<p className="text-sm text-gray-500">
					You are not assigned to a section yet, so you cannot post or see
					doubts. Ask your admin to assign your section.
				</p>
			) : (
				<form
					onSubmit={ask}
					className="space-y-2 rounded-lg border border-gray-200 p-4"
				>
					<h2 className="text-sm font-semibold text-gray-700">Ask a doubt</h2>
					<input
						className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
						placeholder="Title (e.g. Doubt in normalization)"
						value={title}
						onChange={(e) => setTitle(e.target.value)}
						required
					/>
					<textarea
						className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
						placeholder="Describe your doubt..."
						rows={3}
						value={body}
						onChange={(e) => setBody(e.target.value)}
						required
					/>
					{formError ? (
						<p className="text-sm text-red-600">{formError}</p>
					) : null}
					<button
						type="submit"
						disabled={submitting}
						className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
					>
						{submitting ? "Posting..." : "Post doubt"}
					</button>
				</form>
			)}

			<section className="space-y-3">
				<h2 className="text-sm font-semibold text-gray-700">
					Your section's doubts
				</h2>
				{loading ? (
					<p className="text-sm text-gray-500">Loading...</p>
				) : error ? (
					<p className="text-sm text-red-600">{error}</p>
				) : doubts.length === 0 ? (
					<p className="text-sm text-gray-500">No doubts yet.</p>
				) : (
					<ul className="space-y-2">
						{doubts.map((d) => (
							<li key={d.id}>
								<button
									onClick={() => setSelected(d.id)}
									className="w-full rounded-lg border border-gray-200 p-3 text-left hover:bg-gray-50"
								>
									<div className="flex items-center justify-between gap-3">
										<span className="font-medium text-gray-900">
											{d.title}
										</span>
										<span className={statusBadge(d.status === "resolved")}>
											{d.status === "resolved" ? "Resolved" : "Open"}
										</span>
									</div>
									<p className="mt-1 text-xs text-gray-500">
										{d.answer_count} answer
										{d.answer_count === 1 ? "" : "s"}
									</p>
								</button>
							</li>
						))}
					</ul>
				)}
			</section>
		</div>
	)
}
