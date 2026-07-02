/**
 * Campus AI - Student Activities (ECA) page.
 *
 * Place this file at: src/app/dashboard/eca/page.tsx
 *
 * A student logs an extra-curricular activity with proof (starts `pending`),
 * a teacher/TPO verifies or flags it, and only `verified` activities count
 * toward the resume / recruiter view. No AI score - a human confirms proof.
 *
 * Backend endpoints:
 *   POST   /eca   body: { title, category, organization?, description?, evidence_url? }
 *   GET    /eca/me
 *   DELETE /eca/{id}
 */

"use client"

import { useEffect, useState } from "react"
import { api, ApiError } from "@/lib/api"

type EcaStatus = "pending" | "verified" | "flagged"

const CATEGORIES = [
	"sports",
	"cultural",
	"technical",
	"volunteering",
	"leadership",
	"other",
] as const
type Category = (typeof CATEGORIES)[number]

type Eca = {
	id: number
	student_id: number
	title: string
	category: Category
	organization: string | null
	description: string | null
	evidence_url: string | null
	status: EcaStatus
	review_note: string | null
}

type EcaForm = {
	title: string
	category: Category
	organization: string
	description: string
	evidence_url: string
}

const EMPTY_FORM: EcaForm = {
	title: "",
	category: "other",
	organization: "",
	description: "",
	evidence_url: "",
}

const STATUS_STYLES: Record<EcaStatus, string> = {
	pending: "bg-amber-500/15 text-amber-600 dark:text-amber-300",
	verified: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-300",
	flagged: "bg-red-500/15 text-red-300",
}

const CATEGORY_STYLES: Record<Category, string> = {
	sports: "bg-sky-500/15 text-sky-600 dark:text-sky-300",
	cultural: "bg-pink-500/15 text-pink-600 dark:text-pink-300",
	technical: "bg-indigo-500/15 text-indigo-600 dark:text-indigo-300",
	volunteering: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-300",
	leadership: "bg-amber-500/15 text-amber-600 dark:text-amber-300",
	other: "bg-slate-500/15 text-slate-600 dark:text-slate-300",
}

export default function EcaPage() {
	const [items, setItems] = useState<Eca[]>([])
	const [loading, setLoading] = useState(true)
	const [submitting, setSubmitting] = useState(false)
	const [error, setError] = useState<string | null>(null)
	const [form, setForm] = useState<EcaForm>(EMPTY_FORM)

	async function load() {
		setLoading(true)
		setError(null)
		try {
			setItems(await api.get<Eca[]>("/eca/me"))
		} catch (err) {
			setError(
				err instanceof ApiError ? err.message : "Could not load activities.",
			)
		} finally {
			setLoading(false)
		}
	}

	useEffect(() => {
		load()
	}, [])

	function setField(key: keyof EcaForm, val: string) {
		setForm((prev) => ({ ...prev, [key]: val }) as EcaForm)
	}

	async function handleSubmit(e: React.FormEvent) {
		e.preventDefault()
		setError(null)
		setSubmitting(true)
		try {
			const payload: Record<string, unknown> = {
				title: form.title.trim(),
				category: form.category,
			}
			if (form.organization.trim())
				payload.organization = form.organization.trim()
			if (form.description.trim())
				payload.description = form.description.trim()
			if (form.evidence_url.trim())
				payload.evidence_url = form.evidence_url.trim()

			await api.post<Eca>("/eca", payload)
			setForm(EMPTY_FORM)
			await load()
		} catch (err) {
			setError(
				err instanceof ApiError
					? err.message
					: "Could not log the activity.",
			)
		} finally {
			setSubmitting(false)
		}
	}

	async function remove(item: Eca) {
		setError(null)
		try {
			await api.delete(`/eca/${item.id}`)
			await load()
		} catch (err) {
			setError(
				err instanceof ApiError
					? err.message
					: "Could not delete the activity.",
			)
		}
	}

	const inputClass =
		"mt-1 w-full rounded-lg border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-900 px-3 py-2 text-sm outline-none focus:border-indigo-400"

	return (
		<div>
			<h2 className="text-2xl font-bold">My Activities</h2>
			<p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
				Log extra-curriculars (sports, cultural, leadership...) with proof. A
				teacher or TPO verifies it — only verified activities show on your
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
						<label className="text-sm text-slate-600 dark:text-slate-300">Title *</label>
						<input
							required
							value={form.title}
							onChange={(e) => setField("title", e.target.value)}
							className={inputClass}
							placeholder="Inter-college Football Captain"
						/>
					</div>
					<div>
						<label className="text-sm text-slate-600 dark:text-slate-300">Category *</label>
						<select
							value={form.category}
							onChange={(e) => setField("category", e.target.value)}
							className={`${inputClass} capitalize`}
						>
							{CATEGORIES.map((c) => (
								<option key={c} value={c} className="capitalize">
									{c}
								</option>
							))}
						</select>
					</div>
					<div>
						<label className="text-sm text-slate-600 dark:text-slate-300">Organization</label>
						<input
							value={form.organization}
							onChange={(e) => setField("organization", e.target.value)}
							className={inputClass}
							placeholder="Sports Committee"
						/>
					</div>
					<div>
						<label className="text-sm text-slate-600 dark:text-slate-300">Evidence URL</label>
						<input
							value={form.evidence_url}
							onChange={(e) => setField("evidence_url", e.target.value)}
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
							placeholder="What was your role / achievement?"
						/>
					</div>
				</div>
				<button
					type="submit"
					disabled={submitting}
					className="mt-5 rounded-lg bg-gradient-to-r from-indigo-500 to-violet-500 px-5 py-2.5 text-sm font-medium text-white transition hover:opacity-90 disabled:opacity-50"
				>
					{submitting ? "Saving..." : "Log activity"}
				</button>
			</form>

			{/* Activity list */}
			<div className="mt-8">
				{loading ? (
					<p className="text-slate-500 dark:text-slate-400">Loading your activities...</p>
				) : items.length === 0 ? (
					<p className="text-slate-500 dark:text-slate-400">
						No activities logged yet. Add your first one above.
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
										<span className="font-medium">{item.title}</span>
										<span
											className={`rounded-full px-2 py-0.5 text-xs capitalize ${CATEGORY_STYLES[item.category]}`}
										>
											{item.category}
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

								{item.organization && (
									<p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
										{item.organization}
									</p>
								)}
								{item.description && (
									<p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
										{item.description}
									</p>
								)}
								{item.evidence_url && (
									<a
										href={item.evidence_url}
										target="_blank"
										rel="noreferrer"
										className="mt-1 inline-block text-xs text-indigo-600 dark:text-indigo-300 underline"
									>
										{item.evidence_url}
									</a>
								)}
								{item.review_note && (
									<p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
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
