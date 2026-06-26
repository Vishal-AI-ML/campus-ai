/**
 * Campus AI - Admin: Academic Calendar.
 *
 * Place this file at: src/app/dashboard/calendar/page.tsx
 *
 * Admins add calendar entries (holiday / exam / event / deadline) targeted at
 * everyone or a single role, and see / delete every entry here. Other roles
 * see their relevant upcoming entries on their Overview.
 *
 * Backend endpoints:
 *   GET    /calendar?upcoming={bool}  -> [{ id, title, description, event_date, end_date, category, audience, ... }]
 *   POST   /calendar                  body { title, description?, event_date, end_date?, category, audience }
 *   DELETE /calendar/{id}             -> 204
 */

"use client"

import { useEffect, useState } from "react"
import { api, ApiError } from "@/lib/api"
import { useCurrentUser } from "@/lib/auth"

type Category = "holiday" | "exam" | "event" | "deadline"
type Audience = "all" | "student" | "teacher" | "tpo"

type CalendarEvent = {
	id: number
	title: string
	description: string | null
	event_date: string
	end_date: string | null
	category: Category
	audience: Audience
	created_by_id: number | null
	created_at: string
}

const CATEGORIES: { value: Category; label: string }[] = [
	{ value: "event", label: "Event" },
	{ value: "holiday", label: "Holiday" },
	{ value: "exam", label: "Exam" },
	{ value: "deadline", label: "Deadline" },
]

const AUDIENCES: { value: Audience; label: string }[] = [
	{ value: "all", label: "Everyone" },
	{ value: "student", label: "Students" },
	{ value: "teacher", label: "Teachers" },
	{ value: "tpo", label: "TPOs" },
]

const CATEGORY_STYLE: Record<Category, string> = {
	holiday: "bg-rose-500/15 text-rose-300",
	exam: "bg-amber-500/15 text-amber-300",
	event: "bg-indigo-500/15 text-indigo-300",
	deadline: "bg-pink-500/15 text-pink-300",
}

const CATEGORY_LABEL: Record<Category, string> = {
	holiday: "Holiday",
	exam: "Exam",
	event: "Event",
	deadline: "Deadline",
}

const AUDIENCE_LABEL: Record<Audience, string> = {
	all: "Everyone",
	student: "Students",
	teacher: "Teachers",
	tpo: "TPOs",
}

const inputClass =
	"mt-1 w-full rounded-lg border border-white/10 bg-slate-900 px-3 py-2 text-sm outline-none focus:border-indigo-400"

// Treat a "YYYY-MM-DD" value as a local day (avoid UTC shifting it a day back).
function formatDay(iso: string): string {
	const d = new Date(`${iso}T00:00:00`)
	if (Number.isNaN(d.getTime())) return iso
	return d.toLocaleDateString(undefined, {
		weekday: "short",
		day: "numeric",
		month: "short",
		year: "numeric",
	})
}

function dateRange(ev: CalendarEvent): string {
	if (ev.end_date && ev.end_date !== ev.event_date) {
		return `${formatDay(ev.event_date)} - ${formatDay(ev.end_date)}`
	}
	return formatDay(ev.event_date)
}

export default function CalendarPage() {
	const { user } = useCurrentUser()

	const [items, setItems] = useState<CalendarEvent[]>([])
	const [loading, setLoading] = useState(true)
	const [error, setError] = useState<string | null>(null)

	const [title, setTitle] = useState("")
	const [description, setDescription] = useState("")
	const [eventDate, setEventDate] = useState("")
	const [endDate, setEndDate] = useState("")
	const [category, setCategory] = useState<Category>("event")
	const [audience, setAudience] = useState<Audience>("all")
	const [posting, setPosting] = useState(false)
	const [postError, setPostError] = useState<string | null>(null)
	const [deletingId, setDeletingId] = useState<number | null>(null)

	async function load() {
		setLoading(true)
		setError(null)
		try {
			setItems(await api.get<CalendarEvent[]>("/calendar"))
		} catch (err) {
			setError(
				err instanceof ApiError ? err.message : "Could not load calendar.",
			)
		} finally {
			setLoading(false)
		}
	}

	useEffect(() => {
		load()
	}, [])

	async function post() {
		if (!title.trim() || !eventDate) {
			setPostError("Title and date are required.")
			return
		}
		if (endDate && endDate < eventDate) {
			setPostError("End date cannot be before the start date.")
			return
		}
		setPosting(true)
		setPostError(null)
		try {
			const payload = {
				title: title.trim(),
				description: description.trim() || null,
				event_date: eventDate,
				end_date: endDate || null,
				category,
				audience,
			}
			await api.post("/calendar", payload)
			setTitle("")
			setDescription("")
			setEventDate("")
			setEndDate("")
			setCategory("event")
			setAudience("all")
			await load()
		} catch (err) {
			setPostError(
				err instanceof ApiError ? err.message : "Could not add event.",
			)
		} finally {
			setPosting(false)
		}
	}

	async function remove(id: number) {
		setDeletingId(id)
		setError(null)
		try {
			await api.delete(`/calendar/${id}`)
			setItems((prev) => prev.filter((e) => e.id !== id))
		} catch (err) {
			setError(
				err instanceof ApiError ? err.message : "Could not delete event.",
			)
		} finally {
			setDeletingId(null)
		}
	}

	if (user && user.role !== "admin") {
		return (
			<div>
				<h2 className="text-2xl font-bold">Academic Calendar</h2>
				<p className="mt-2 text-slate-400">
					Only admins can manage the calendar. Your upcoming events appear on
					your Overview.
				</p>
			</div>
		)
	}

	return (
		<div>
			<h2 className="text-2xl font-bold">Academic Calendar</h2>
			<p className="mt-1 text-sm text-slate-400">
				Add holidays, exams, events and deadlines for the whole institute or a
				single role.
			</p>

			{/* Composer */}
			<div className="mt-6 rounded-2xl border border-white/10 bg-white/5 p-6">
				<h3 className="text-lg font-semibold">New calendar entry</h3>
				<div className="mt-3 grid gap-3">
					<div>
						<label className="text-sm text-slate-400">Title</label>
						<input
							value={title}
							onChange={(e) => setTitle(e.target.value)}
							className={inputClass}
							placeholder="Semester exams begin"
						/>
					</div>
					<div>
						<label className="text-sm text-slate-400">
							Description (optional)
						</label>
						<textarea
							value={description}
							onChange={(e) => setDescription(e.target.value)}
							rows={2}
							className={inputClass}
							placeholder="Details, venue, instructions..."
						/>
					</div>
					<div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
						<div>
							<label className="text-sm text-slate-400">Start date</label>
							<input
								type="date"
								value={eventDate}
								onChange={(e) => setEventDate(e.target.value)}
								className={inputClass}
							/>
						</div>
						<div>
							<label className="text-sm text-slate-400">
								End date (optional)
							</label>
							<input
								type="date"
								value={endDate}
								onChange={(e) => setEndDate(e.target.value)}
								className={inputClass}
							/>
						</div>
						<div>
							<label className="text-sm text-slate-400">Category</label>
							<select
								value={category}
								onChange={(e) => setCategory(e.target.value as Category)}
								className={inputClass}
							>
								{CATEGORIES.map((c) => (
									<option key={c.value} value={c.value}>
										{c.label}
									</option>
								))}
							</select>
						</div>
						<div>
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
					{posting ? "Adding..." : "Add to calendar"}
				</button>
			</div>

			{error && (
				<p className="mt-4 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">
					{error}
				</p>
			)}

			{/* List */}
			<div className="mt-6">
				<h3 className="text-lg font-semibold">All entries</h3>
				{loading ? (
					<p className="mt-3 text-slate-400">Loading...</p>
				) : items.length === 0 ? (
					<p className="mt-3 text-slate-400">No calendar entries yet.</p>
				) : (
					<div className="mt-3 space-y-3">
						{items.map((ev) => (
							<div
								key={ev.id}
								className="rounded-2xl border border-white/10 bg-white/5 p-5"
							>
								<div className="flex items-start justify-between gap-3">
									<div>
										<div className="flex flex-wrap items-center gap-2">
											<span className="font-semibold">{ev.title}</span>
											<span
												className={`rounded-full px-2 py-0.5 text-xs ${CATEGORY_STYLE[ev.category]}`}
											>
												{CATEGORY_LABEL[ev.category]}
											</span>
											<span className="rounded-full bg-white/10 px-2 py-0.5 text-xs text-slate-300">
												{AUDIENCE_LABEL[ev.audience]}
											</span>
										</div>
										<p className="mt-1 text-xs text-slate-400">
											{dateRange(ev)}
										</p>
									</div>
									<button
										onClick={() => remove(ev.id)}
										disabled={deletingId === ev.id}
										className="rounded-lg border border-red-400/30 px-3 py-1 text-xs text-red-300 transition hover:bg-red-400/10 disabled:opacity-40"
									>
										{deletingId === ev.id ? "Deleting..." : "Delete"}
									</button>
								</div>
								{ev.description && (
									<p className="mt-2 whitespace-pre-wrap text-sm text-slate-300">
										{ev.description}
									</p>
								)}
							</div>
						))}
					</div>
				)}
			</div>
		</div>
	)
}
