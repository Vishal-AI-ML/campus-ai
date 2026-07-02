/**
 * Campus AI - Student Internships / OJT page.
 *
 * Place this file at: src/app/dashboard/internships/page.tsx
 *
 * A student logs an internship / OJT with details + proof (starts `pending`),
 * a teacher/TPO verifies or flags it, and only `verified` internships count
 * toward the resume / recruiter view. No AI score - a human confirms proof.
 *
 * Backend endpoints:
 *   POST   /internships
 *   GET    /internships/me
 *   DELETE /internships/{id}
 */

"use client"

import { useEffect, useState } from "react"
import { api, ApiError } from "@/lib/api"

type InternshipStatus = "pending" | "verified" | "flagged"

const TYPES = [
	"internship",
	"ojt",
	"apprenticeship",
	"training",
	"other",
] as const
type InternType = (typeof TYPES)[number]

const MODES = ["onsite", "remote", "hybrid"] as const

type Internship = {
	id: number
	student_id: number
	organization: string
	role_title: string
	internship_type: InternType
	mode: string | null
	location: string | null
	description: string | null
	skills_used: string | null
	start_date: string | null
	end_date: string | null
	is_ongoing: boolean
	certificate_url: string | null
	status: InternshipStatus
	review_note: string | null
}

type InternForm = {
	organization: string
	role_title: string
	internship_type: InternType
	mode: string
	location: string
	start_date: string
	end_date: string
	is_ongoing: boolean
	skills_used: string
	certificate_url: string
	description: string
}

const EMPTY_FORM: InternForm = {
	organization: "",
	role_title: "",
	internship_type: "internship",
	mode: "",
	location: "",
	start_date: "",
	end_date: "",
	is_ongoing: false,
	skills_used: "",
	certificate_url: "",
	description: "",
}

const STATUS_STYLES: Record<InternshipStatus, string> = {
	pending: "bg-amber-500/15 text-amber-600 dark:text-amber-300",
	verified: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-300",
	flagged: "bg-red-500/15 text-red-300",
}

export default function InternshipsPage() {
	const [items, setItems] = useState<Internship[]>([])
	const [loading, setLoading] = useState(true)
	const [submitting, setSubmitting] = useState(false)
	const [error, setError] = useState<string | null>(null)
	const [form, setForm] = useState<InternForm>(EMPTY_FORM)

	async function load() {
		setLoading(true)
		setError(null)
		try {
			setItems(await api.get<Internship[]>("/internships/me"))
		} catch (err) {
			setError(
				err instanceof ApiError ? err.message : "Could not load internships.",
			)
		} finally {
			setLoading(false)
		}
	}

	useEffect(() => {
		load()
	}, [])

	function setField(key: keyof InternForm, val: string | boolean) {
		setForm((prev) => ({ ...prev, [key]: val }) as InternForm)
	}

	async function handleSubmit(e: React.FormEvent) {
		e.preventDefault()
		setError(null)
		setSubmitting(true)
		try {
			const payload: Record<string, unknown> = {
				organization: form.organization.trim(),
				role_title: form.role_title.trim(),
				internship_type: form.internship_type,
				is_ongoing: form.is_ongoing,
			}
			if (form.mode.trim()) payload.mode = form.mode.trim()
			if (form.location.trim()) payload.location = form.location.trim()
			if (form.start_date) payload.start_date = form.start_date
			if (!form.is_ongoing && form.end_date) payload.end_date = form.end_date
			if (form.skills_used.trim())
				payload.skills_used = form.skills_used.trim()
			if (form.certificate_url.trim())
				payload.certificate_url = form.certificate_url.trim()
			if (form.description.trim())
				payload.description = form.description.trim()

			await api.post<Internship>("/internships", payload)
			setForm(EMPTY_FORM)
			await load()
		} catch (err) {
			setError(
				err instanceof ApiError
					? err.message
					: "Could not log the internship.",
			)
		} finally {
			setSubmitting(false)
		}
	}

	async function remove(item: Internship) {
		setError(null)
		try {
			await api.delete(`/internships/${item.id}`)
			await load()
		} catch (err) {
			setError(
				err instanceof ApiError
					? err.message
					: "Could not delete the internship.",
			)
		}
	}

	const inputClass =
		"mt-1 w-full rounded-lg border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-900 px-3 py-2 text-sm outline-none focus:border-indigo-400"

	return (
		<div>
			<h2 className="text-2xl font-bold">My Internships & OJT</h2>
			<p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
				Log internships, on-the-job training and apprenticeships with proof. A
				teacher or TPO verifies it — only verified work experience shows on your
				resume and to recruiters.
			</p>

			{error && (
				<p className="mt-4 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">
					{error}
				</p>
			)}

			{/* Log form */}
			<form
				onSubmit={handleSubmit}
				className="mt-6 rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-900 p-6"
			>
				<div className="grid gap-4 sm:grid-cols-2">
					<div>
						<label className="text-sm text-slate-600 dark:text-slate-300">Organization *</label>
						<input
							required
							value={form.organization}
							onChange={(e) => setField("organization", e.target.value)}
							className={inputClass}
							placeholder="Infosys"
						/>
					</div>
					<div>
						<label className="text-sm text-slate-600 dark:text-slate-300">Role / Title *</label>
						<input
							required
							value={form.role_title}
							onChange={(e) => setField("role_title", e.target.value)}
							className={inputClass}
							placeholder="Software Engineering Intern"
						/>
					</div>
					<div>
						<label className="text-sm text-slate-600 dark:text-slate-300">Type *</label>
						<select
							value={form.internship_type}
							onChange={(e) => setField("internship_type", e.target.value)}
							className={`${inputClass} capitalize`}
						>
							{TYPES.map((t) => (
								<option key={t} value={t} className="capitalize">
									{t}
								</option>
							))}
						</select>
					</div>
					<div>
						<label className="text-sm text-slate-600 dark:text-slate-300">Mode</label>
						<select
							value={form.mode}
							onChange={(e) => setField("mode", e.target.value)}
							className={`${inputClass} capitalize`}
						>
							<option value="">—</option>
							{MODES.map((m) => (
								<option key={m} value={m} className="capitalize">
									{m}
								</option>
							))}
						</select>
					</div>
					<div>
						<label className="text-sm text-slate-600 dark:text-slate-300">Location</label>
						<input
							value={form.location}
							onChange={(e) => setField("location", e.target.value)}
							className={inputClass}
							placeholder="Bengaluru"
						/>
					</div>
					<div>
						<label className="text-sm text-slate-600 dark:text-slate-300">Skills used</label>
						<input
							value={form.skills_used}
							onChange={(e) => setField("skills_used", e.target.value)}
							className={inputClass}
							placeholder="Python, FastAPI, PostgreSQL"
						/>
					</div>
					<div>
						<label className="text-sm text-slate-600 dark:text-slate-300">Start date</label>
						<input
							type="date"
							value={form.start_date}
							onChange={(e) => setField("start_date", e.target.value)}
							className={inputClass}
						/>
					</div>
					<div>
						<label className="text-sm text-slate-600 dark:text-slate-300">End date</label>
						<input
							type="date"
							value={form.end_date}
							disabled={form.is_ongoing}
							onChange={(e) => setField("end_date", e.target.value)}
							className={`${inputClass} disabled:opacity-40`}
						/>
					</div>
					<div className="flex items-center gap-2">
						<input
							id="is_ongoing"
							type="checkbox"
							checked={form.is_ongoing}
							onChange={(e) => setField("is_ongoing", e.target.checked)}
							className="h-4 w-4 rounded border-slate-300 dark:border-white/15 bg-white dark:bg-slate-900"
						/>
						<label htmlFor="is_ongoing" className="text-sm text-slate-600 dark:text-slate-300">
							Currently ongoing
						</label>
					</div>
					<div>
						<label className="text-sm text-slate-600 dark:text-slate-300">Certificate URL</label>
						<input
							value={form.certificate_url}
							onChange={(e) => setField("certificate_url", e.target.value)}
							className={inputClass}
							placeholder="https://.../certificate.pdf"
						/>
					</div>
					<div className="sm:col-span-2">
						<label className="text-sm text-slate-600 dark:text-slate-300">Description</label>
						<textarea
							value={form.description}
							onChange={(e) => setField("description", e.target.value)}
							className={inputClass}
							rows={3}
							placeholder="What did you work on / achieve?"
						/>
					</div>
				</div>
				<button
					type="submit"
					disabled={submitting}
					className="mt-5 rounded-lg bg-gradient-to-r from-indigo-500 to-violet-500 px-5 py-2.5 text-sm font-medium text-white transition hover:opacity-90 disabled:opacity-50"
				>
					{submitting ? "Saving..." : "Log internship"}
				</button>
			</form>

			{/* List */}
			<div className="mt-8">
				{loading ? (
					<p className="text-slate-500 dark:text-slate-400">Loading your internships...</p>
				) : items.length === 0 ? (
					<p className="text-slate-500 dark:text-slate-400">
						No internships logged yet. Add your first one above.
					</p>
				) : (
					<div className="space-y-3">
						{items.map((item) => (
							<div
								key={item.id}
								className="rounded-xl border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-900 p-4"
							>
								<div className="flex flex-wrap items-center justify-between gap-2">
									<div className="flex flex-wrap items-center gap-2">
										<span className="font-medium">
											{item.role_title} @ {item.organization}
										</span>
										<span className="rounded-full bg-slate-500/15 px-2 py-0.5 text-xs capitalize text-slate-600 dark:text-slate-300">
											{item.internship_type}
										</span>
										<span
											className={`rounded-full px-2 py-0.5 text-xs capitalize ${STATUS_STYLES[item.status]}`}
										>
											{item.status}
										</span>
									</div>
									<button
										onClick={() => remove(item)}
										className="rounded-lg border border-slate-300 dark:border-white/15 px-3 py-1 text-xs transition hover:bg-slate-100 dark:hover:bg-white/10"
									>
										Delete
									</button>
								</div>

								<p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
									{[
										item.mode,
										item.location,
										item.start_date,
										item.is_ongoing ? "ongoing" : item.end_date,
									]
										.filter(Boolean)
										.join(" · ")}
								</p>
								{item.skills_used && (
									<p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
										Skills: {item.skills_used}
									</p>
								)}
								{item.description && (
									<p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
										{item.description}
									</p>
								)}
								{item.certificate_url && (
									<a
										href={item.certificate_url}
										target="_blank"
										rel="noreferrer"
										className="mt-1 inline-block text-xs text-indigo-600 dark:text-indigo-300 underline"
									>
										{item.certificate_url}
									</a>
								)}
								{item.review_note && (
									<p className="mt-2 text-xs text-amber-600/80">
										Reviewer note: {item.review_note}
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
