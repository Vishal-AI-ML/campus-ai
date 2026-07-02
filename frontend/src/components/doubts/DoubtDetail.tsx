"use client"

// Shared doubt detail view: shows a doubt + its answers, and lets the viewer
// post an answer, toggle an upvote, and (asker/staff) accept an answer.

import { useCallback, useEffect, useState, type FormEvent } from "react"
import { api, ApiError } from "@/lib/api"
import { formatDateTime, type DoubtDetailOut, type MeUser } from "./doubtsApi"

// Roles allowed to accept any doubt's answer (mirrors the backend's staff set).
const STAFF_ROLES = ["teacher", "admin", "tpo"]

type Props = {
	doubtId: number
	me: MeUser
	onBack: () => void
	onChanged?: () => void
}

export default function DoubtDetail({ doubtId, me, onBack, onChanged }: Props) {
	const [doubt, setDoubt] = useState<DoubtDetailOut | null>(null)
	const [loading, setLoading] = useState(true)
	const [error, setError] = useState<string | null>(null)
	const [answerBody, setAnswerBody] = useState("")
	const [submitting, setSubmitting] = useState(false)

	const load = useCallback(() => {
		setLoading(true)
		setError(null)
		api
			.get(`/doubts/${doubtId}`)
			.then((data) => setDoubt(data as DoubtDetailOut))
			.catch((e) =>
				setError(e instanceof ApiError ? e.message : "Failed to load doubt")
			)
			.finally(() => setLoading(false))
	}, [doubtId])

	useEffect(() => {
		load()
	}, [load])

	async function postAnswer(e: FormEvent) {
		e.preventDefault()
		if (!answerBody.trim()) return
		setSubmitting(true)
		try {
			await api.post(`/doubts/${doubtId}/answers`, { body: answerBody.trim() })
			setAnswerBody("")
			load()
			onChanged?.()
		} catch (e) {
			setError(e instanceof ApiError ? e.message : "Failed to post answer")
		} finally {
			setSubmitting(false)
		}
	}

	async function toggleUpvote(answerId: number) {
		try {
			await api.post(`/doubts/answers/${answerId}/upvote`, {})
			load()
		} catch (e) {
			setError(e instanceof ApiError ? e.message : "Failed to upvote")
		}
	}

	async function acceptAnswer(answerId: number) {
		try {
			await api.post(`/doubts/${doubtId}/answers/${answerId}/accept`, {})
			load()
			onChanged?.()
		} catch (e) {
			setError(e instanceof ApiError ? e.message : "Failed to accept answer")
		}
	}

	const statusBadge = (resolved: boolean) =>
		resolved
			? "shrink-0 rounded-full bg-green-100 px-2 py-0.5 text-xs text-green-700"
			: "shrink-0 rounded-full bg-amber-100 px-2 py-0.5 text-xs text-amber-700"

	return (
		<div className="space-y-4">
			<button
				onClick={onBack}
				className="text-sm text-blue-600 hover:underline"
			>
				← Back to doubts
			</button>

			{loading ? (
				<p className="text-sm text-gray-500 dark:text-slate-400">Loading...</p>
			) : error ? (
				<p className="text-sm text-red-600">{error}</p>
			) : !doubt ? null : (
				<>
					<div className="rounded-lg border border-gray-200 dark:border-white/10 p-4">
						<div className="flex items-start justify-between gap-3">
							<h2 className="font-semibold text-gray-900 dark:text-slate-100">{doubt.title}</h2>
							<span className={statusBadge(doubt.status === "resolved")}>
								{doubt.status === "resolved" ? "Resolved" : "Open"}
							</span>
						</div>
						<p className="mt-1 whitespace-pre-wrap text-sm text-gray-700 dark:text-slate-300">
							{doubt.body}
						</p>
						<p className="mt-2 text-xs text-gray-400 dark:text-slate-500">
							{formatDateTime(doubt.created_at)}
						</p>
					</div>

					<section className="space-y-3">
						<h3 className="text-sm font-semibold text-gray-700 dark:text-slate-300">
							{doubt.answers.length} answer
							{doubt.answers.length === 1 ? "" : "s"}
						</h3>
						{doubt.answers.length === 0 ? (
							<p className="text-sm text-gray-500 dark:text-slate-400">
								No answers yet — be the first to help.
							</p>
						) : null}
						{doubt.answers.map((a) => {
							const canAccept =
								!a.is_accepted &&
								(STAFF_ROLES.includes(me.role) ||
									doubt.asked_by_id === me.id)
							return (
								<div
									key={a.id}
									className={
										a.is_accepted
											? "rounded-lg border border-green-300 bg-green-50 p-4"
											: "rounded-lg border border-gray-200 dark:border-white/10 p-4"
									}
								>
									{a.is_accepted ? (
										<p className="mb-1 text-xs font-medium text-green-700">
											✅ Accepted answer
										</p>
									) : null}
									<p className="whitespace-pre-wrap text-sm text-gray-700 dark:text-slate-300">
										{a.body}
									</p>
									<div className="mt-2 flex items-center gap-3">
										<button
											onClick={() => toggleUpvote(a.id)}
											className={
												a.viewer_has_upvoted
													? "rounded-md bg-blue-600 px-2 py-1 text-xs text-white"
													: "rounded-md border border-gray-300 dark:border-white/15 px-2 py-1 text-xs text-gray-700 dark:text-slate-300 hover:bg-gray-50 dark:hover:bg-white/5"
											}
										>
											👍 {a.upvote_count}
										</button>
										{canAccept ? (
											<button
												onClick={() => acceptAnswer(a.id)}
												className="rounded-md border border-green-400 px-2 py-1 text-xs text-green-700 hover:bg-green-50"
											>
												Accept
											</button>
										) : null}
										<span className="text-xs text-gray-400 dark:text-slate-500">
											{formatDateTime(a.created_at)}
										</span>
									</div>
								</div>
							)
						})}
					</section>

					<form
						onSubmit={postAnswer}
						className="space-y-2 rounded-lg border border-gray-200 dark:border-white/10 p-4"
					>
						<h3 className="text-sm font-semibold text-gray-700 dark:text-slate-300">
							Post an answer
						</h3>
						<textarea
							className="w-full rounded-md border border-gray-300 dark:border-white/15 px-3 py-2 text-sm"
							placeholder="Write your answer..."
							rows={3}
							value={answerBody}
							onChange={(e) => setAnswerBody(e.target.value)}
						/>
						<button
							type="submit"
							disabled={submitting}
							className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
						>
							{submitting ? "Posting..." : "Post answer"}
						</button>
					</form>
				</>
			)}
		</div>
	)
}
