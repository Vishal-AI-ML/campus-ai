/**
 * Campus AI - Student AI Mentor chat page.
 *
 * Place this file at: src/app/dashboard/mentor/page.tsx
 *
 * A chat UI for the AI Career Mentor. Every answer is grounded ONLY on the
 * student's VERIFIED profile (verified skills, verified project contributions,
 * attendance %, CGPA) - the backend builds that context, so advice can't be
 * based on unproven claims.
 *
 * Backend endpoint:
 *   POST /mentor/chat
 *     body     -> { question: string, history: [{ role: "user" | "assistant", content: string }] }
 *     response -> { answer: string, provider: string }
 *     502 when the AI worker is not running.
 */

"use client"

import { useEffect, useRef, useState } from "react"
import { api, ApiError } from "@/lib/api"

type Turn = {
	role: "user" | "assistant"
	content: string
}

type MentorChatResponse = {
	answer: string
	provider: string
}

const SUGGESTIONS = [
	"Backend role ke liye mera skill gap kya hai?",
	"Mere verified projects ke hisab se kaunsi jobs suit karengi?",
	"Placement ke liye agle 30 din ka plan banao.",
]

export default function MentorPage() {
	const [messages, setMessages] = useState<Turn[]>([])
	const [input, setInput] = useState("")
	const [loading, setLoading] = useState(false)
	const [error, setError] = useState<string | null>(null)
	const [provider, setProvider] = useState<string | null>(null)
	const endRef = useRef<HTMLDivElement | null>(null)

	// Keep the latest message in view as the conversation grows.
	useEffect(() => {
		endRef.current?.scrollIntoView({ behavior: "smooth" })
	}, [messages, loading])

	async function send(question: string) {
		const trimmed = question.trim()
		if (!trimmed || loading) return
		setError(null)
		// Prior turns become the history; the new question is sent separately.
		const history = messages
		setMessages((prev) => [...prev, { role: "user", content: trimmed }])
		setInput("")
		setLoading(true)
		try {
			const res = await api.post<MentorChatResponse>("/mentor/chat", {
				question: trimmed,
				history,
			})
			setMessages((prev) => [
				...prev,
				{ role: "assistant", content: res.answer },
			])
			setProvider(res.provider)
		} catch (err) {
			setError(
				err instanceof ApiError
					? err.message
					: "AI mentor is unavailable right now.",
			)
		} finally {
			setLoading(false)
		}
	}

	function onSubmit(e: React.FormEvent) {
		e.preventDefault()
		send(input)
	}

	return (
		<div className="flex h-[calc(100vh-8rem)] flex-col">
			<div className="flex items-center justify-between">
				<div>
					<h2 className="text-2xl font-bold">AI Career Mentor</h2>
					<p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
						Grounded only on your verified profile - skills, projects,
						attendance, and CGPA.
					</p>
				</div>
				{provider && (
					<span className="rounded-full bg-slate-100 dark:bg-slate-800 px-2 py-0.5 text-xs text-slate-500 dark:text-slate-400">
						{provider}
					</span>
				)}
			</div>

			{/* Conversation */}
			<div className="mt-4 flex-1 space-y-3 overflow-y-auto rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-900 p-4">
				{messages.length === 0 && !loading ? (
					<div className="flex h-full flex-col items-center justify-center text-center">
						<p className="text-slate-500 dark:text-slate-400">
							Apne career, skills ya placement ke baare me kuch bhi poochho.
						</p>
						<div className="mt-4 flex flex-wrap justify-center gap-2">
							{SUGGESTIONS.map((s) => (
								<button
									key={s}
									type="button"
									onClick={() => send(s)}
									className="rounded-full border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-900 px-3 py-1.5 text-xs text-slate-600 dark:text-slate-300 hover:border-indigo-400 hover:text-slate-900 dark:hover:text-white"
								>
									{s}
								</button>
							))}
						</div>
					</div>
				) : (
					messages.map((turn, index) => (
						<div
							key={index}
							className={`flex ${
								turn.role === "user" ? "justify-end" : "justify-start"
							}`}
						>
							<div
								className={`max-w-[80%] whitespace-pre-wrap rounded-2xl px-4 py-2 text-sm ${
									turn.role === "user"
										? "bg-gradient-to-r from-indigo-500 to-violet-500 text-white"
										: "bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200"
								}`}
							>
								{turn.content}
							</div>
						</div>
					))
				)}

				{loading && (
					<div className="flex justify-start">
						<div className="rounded-2xl bg-slate-100 dark:bg-slate-800 px-4 py-2 text-sm text-slate-500 dark:text-slate-400">
							Mentor soch raha hai...
						</div>
					</div>
				)}

				<div ref={endRef} />
			</div>

			{error && (
				<p className="mt-3 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">
					{error}
				</p>
			)}

			{/* Composer */}
			<form onSubmit={onSubmit} className="mt-3 flex gap-2">
				<input
					value={input}
					onChange={(e) => setInput(e.target.value)}
					placeholder="Apna sawaal type karo..."
					disabled={loading}
					className="flex-1 rounded-lg border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-900 px-3 py-2 text-sm outline-none focus:border-indigo-400 disabled:opacity-60"
				/>
				<button
					type="submit"
					disabled={loading || !input.trim()}
					className="rounded-lg bg-gradient-to-r from-indigo-500 to-violet-500 px-5 py-2 text-sm font-medium text-white disabled:opacity-50"
				>
					Send
				</button>
			</form>
		</div>
	)
}
