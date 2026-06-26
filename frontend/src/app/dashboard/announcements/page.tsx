/**
 * Campus AI - Admin: Announcements.
 *
 * Place this file at: src/app/dashboard/announcements/page.tsx
 *
 * Admins post institute broadcasts targeted at everyone or a single role, and
 * see / delete every announcement here (admins get the full governance list;
 * other roles only see posts meant for them on their Overview feed).
 *
 * Backend endpoints:
 *   GET    /announcements             -> [{ id, title, body, audience, author_id, created_at }]
 *   POST   /announcements             body { title, body, audience }
 *   DELETE /announcements/{id}        -> 204
 */

"use client"

import { useEffect, useState } from "react"
import { api, ApiError } from "@/lib/api"
import { useCurrentUser } from "@/lib/auth"

type Audience = "all" | "student" | "teacher" | "tpo"

type Announcement = {
	id: number
	title: string
	body: string
	audience: Audience
	author_id: number | null
	created_at: string
}

const AUDIENCES: { value: Audience; label: string }[] = [
	{ value: "all", label: "Everyone" },
	{ value: "student", label: "Students" },
	{ value: "teacher", label: "Teachers" },
	{ value: "tpo", label: "TPOs" },
]

const AUDIENCE_LABEL: Record<Audience, string> = {
	all: "Everyone",
	student: "Students",
	teacher: "Teachers",
	tpo: "TPOs",
}

const AUDIENCE_STYLE: Record<Audience, string> = {
	all: "bg-indigo-500/15 text-indigo-300",
	student: "bg-emerald-500/15 text-emerald-300",
	teacher: "bg-sky-500/15 text-sky-300",
	tpo: "bg-violet-500/15 text-violet-300",
}

const inputClass =
	"mt-1 w-full rounded-lg border border-white/10 bg-slate-900 px-3 py-2 text-sm outline-none focus:border-indigo-400"

function formatWhen(iso: string): string {
	const d = new Date(iso)
	if (Number.isNaN(d.getTime())) return iso
	return d.toLocaleString()
}

export default function AnnouncementsPage() {
	const { user } = useCurrentUser()

	const [items, setItems] = useState<Announcement[]>([])
	const [loading, setLoading] = useState(true)
	const [error, setError] = useState<string | null>(null)

	const [title, setTitle] = useState("")
	const [body, setBody] = useState("")
	const [audience, setAudience] = useState<Audience>("all")
	const [posting, setPosting] = useState(false)
	const [postError, setPostError] = useState<string | null>(null)
	const [deletingId, setDeletingId] = useState<number | null>(null)

	async function load() {
		setLoading(true)
		setError(null)
		try {
			setItems(await api.get<Announcement[]>("/announcements"))
		} catch (err) {
			setError(
				err instanceof ApiError
					? err.message
					: "Could not load announcements.",
			)
		} finally {
			setLoading(false)
		}
	}

	useEffect(() => {
		load()
	}, [])

	async function post() {
		if (!title.trim() || !body.trim()) {
			setPostError("Title and message are required.")
			return
		}
		setPosting(true)
		setPostError(null)
		try {
			const payload = {
				title: title.trim(),
				body: body.trim(),
				audience,
			}
			await api.post("/announcements", payload)
			setTitle("")
			setBody("")
			setAudience("all")
			await load()
		} catch (err) {
			setPostError(
				err instanceof ApiError ? err.message : "Could not post announcement.",
			)
		} finally {
			setPosting(false)
		}
	}

	async function remove(id: number) {
		setDeletingId(id)
		setError(null)
		try {
			await api.delete(`/announcements/${id}`)
			setItems((prev) => prev.filter((a) => a.id !== id))
		} catch (err) {
			setError(
				err instanceof ApiError
					? err.message
					: "Could not delete announcement.",
			)
		} finally {
			setDeletingId(null)
		}
	}

	if (user && user.role !== "admin") {
		return (
			<div>
				<h2 className="text-2xl font-bold">Announcements</h2>
				<p className="mt-2 text-slate-400">
					Only admins can post announcements. Your announcements appear on your
					Overview.
				</p>
			</div>
		)
	}

	return (
		<div>
			<h2 className="text-2xl font-bold">Announcements</h2>
			<p className="mt-1 text-sm text-slate-400">
				Broadcast a message to the whole institute or to a single role.
			</p>

			{/* Composer */}
			<div className="mt-6 rounded-2xl border border-white/10 bg-white/5 p-6">
				<h3 className="text-lg font-semibold">New announcement</h3>
				<div className="mt-3 grid gap-3">
					<div>
						<label className="text-sm text-slate-400">Title</label>
						<input
							value={title}
							onChange={(e) => setTitle(e.target.value)}
							className={inputClass}
							placeholder="Mid-semester exam schedule"
						/>
					</div>
					<div>
						<label className="text-sm text-slate-400">Message</label>
						<textarea
							value={body}
							onChange={(e) => setBody(e.target.value)}
							rows={4}
							className={inputClass}
							placeholder="Write the details here..."
						/>
					</div>
					<div className="max-w-xs">
						<label className="text-sm text-slate-400">Audience</label>
						<select
							value={audience}
							onChange={(e) => setAudience(e.target.value as Audience)}
							className={inputClass}
						>
							{AUDIENCES.map((a) => (
								<option key={a.value} value={a.value}>
									{a.label}
								</option>
							))}
						</select>
					</div>
				</div>
				{postError && (
					<p className="mt-3 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">
						{postError}
					</p>
				)}
				<button
					onClick={post}
					disabled={posting}
					className="mt-3 rounded-lg bg-gradient-to-r from-indigo-500 to-violet-500 px-5 py-2.5 text-sm font-medium text-white transition hover:opacity-90 disabled:opacity-40"
				>
					{posting ? "Posting..." : "Post announcement"}
				</button>
			</div>

			{error && (
				<p className="mt-4 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">
					{error}
				</p>
			)}

			{/* List */}
			<div className="mt-6">
				<h3 className="text-lg font-semibold">All announcements</h3>
				{loading ? (
					<p className="mt-3 text-slate-400">Loading...</p>
				) : items.length === 0 ? (
					<p className="mt-3 text-slate-400">No announcements yet.</p>
				) : (
					<div className="mt-3 space-y-3">
						{items.map((a) => (
							<div
								key={a.id}
								className="rounded-2xl border border-white/10 bg-white/5 p-5"
							>
								<div className="flex items-start justify-between gap-3">
									<div>
										<div className="flex items-center gap-2">
											<span className="font-semibold">{a.title}</span>
											<span
												className={`rounded-full px-2 py-0.5 text-xs ${AUDIENCE_STYLE[a.audience]}`}
											>
												{AUDIENCE_LABEL[a.audience]}
											</span>
										</div>
										<p className="mt-1 text-xs text-slate-500">
											{formatWhen(a.created_at)}
										</p>
									</div>
									<button
										onClick={() => remove(a.id)}
										disabled={deletingId === a.id}
										className="rounded-lg border border-red-400/30 px-3 py-1 text-xs text-red-300 transition hover:bg-red-400/10 disabled:opacity-40"
									>
										{deletingId === a.id ? "Deleting..." : "Delete"}
									</button>
								</div>
								<p className="mt-2 whitespace-pre-wrap text-sm text-slate-300">
									{a.body}
								</p>
							</div>
						))}
					</div>
				)}
			</div>
		</div>
	)
}
