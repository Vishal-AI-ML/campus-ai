/**
 * Campus AI - Student Skills page (the verified-data moat).
 *
 * Place this file at: src/app/dashboard/skills/page.tsx
 *
 * A student claims a skill with proof (starts `pending`), sees the AI advisory
 * score + the mentor's verify/flag decision, and can delete their own claims.
 * Only `verified` skills count toward resume / placement eligibility.
 *
 * Backend endpoints:
 *   POST   /skills        body: { name, evidence_url?, evidence_note? }
 *   GET    /skills/me
 *   DELETE /skills/{id}
 */

"use client"

import { useEffect, useState } from "react"
import { api, ApiError } from "@/lib/api"

type SkillStatus = "pending" | "verified" | "flagged"

type Skill = {
	id: number
	student_id: number
	name: string
	evidence_url: string | null
	evidence_note: string | null
	status: SkillStatus
	ai_score: number | null
	review_note: string | null
}

type SkillForm = { name: string; evidence_url: string; evidence_note: string }

const EMPTY_FORM: SkillForm = { name: "", evidence_url: "", evidence_note: "" }

const STATUS_STYLES: Record<SkillStatus, string> = {
	pending: "bg-amber-500/15 text-amber-600 dark:text-amber-300",
	verified: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-300",
	flagged: "bg-red-500/15 text-red-300",
}

export default function SkillsPage() {
	const [skills, setSkills] = useState<Skill[]>([])
	const [loading, setLoading] = useState(true)
	const [submitting, setSubmitting] = useState(false)
	const [error, setError] = useState<string | null>(null)
	const [form, setForm] = useState<SkillForm>(EMPTY_FORM)

	async function load() {
		setLoading(true)
		setError(null)
		try {
			setSkills(await api.get<Skill[]>("/skills/me"))
		} catch (err) {
			setError(
				err instanceof ApiError ? err.message : "Could not load skills.",
			)
		} finally {
			setLoading(false)
		}
	}

	useEffect(() => {
		load()
	}, [])

	function setField(key: keyof SkillForm, val: string) {
		setForm((prev) => ({ ...prev, [key]: val }))
	}

	async function handleSubmit(e: React.FormEvent) {
		e.preventDefault()
		setError(null)
		setSubmitting(true)
		try {
			const payload: Record<string, unknown> = { name: form.name.trim() }
			if (form.evidence_url.trim())
				payload.evidence_url = form.evidence_url.trim()
			if (form.evidence_note.trim())
				payload.evidence_note = form.evidence_note.trim()

			await api.post<Skill>("/skills", payload)
			setForm(EMPTY_FORM)
			await load()
		} catch (err) {
			setError(
				err instanceof ApiError ? err.message : "Could not claim the skill.",
			)
		} finally {
			setSubmitting(false)
		}
	}

	async function remove(skill: Skill) {
		setError(null)
		try {
			await api.delete(`/skills/${skill.id}`)
			await load()
		} catch (err) {
			setError(
				err instanceof ApiError ? err.message : "Could not delete the skill.",
			)
		}
	}

	const inputClass =
		"mt-1 w-full rounded-lg border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-900 px-3 py-2 text-sm outline-none focus:border-indigo-400"

	return (
		<div>
			<h2 className="text-2xl font-bold">My Skills</h2>
			<p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
				Claim a skill with proof. A mentor verifies it — only verified skills
				count toward your resume and placement eligibility.
			</p>

			{error && (
				<p className="mt-4 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">
					{error}
				</p>
			)}

			{/* Claim form */}
			<form
				onSubmit={handleSubmit}
				className="mt-6 rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-900 p-6"
			>
				<div className="grid gap-4 sm:grid-cols-2">
					<div>
						<label className="text-sm text-slate-600 dark:text-slate-300">Skill name *</label>
						<input
							required
							value={form.name}
							onChange={(e) => setField("name", e.target.value)}
							className={inputClass}
							placeholder="FastAPI"
						/>
					</div>
					<div>
						<label className="text-sm text-slate-600 dark:text-slate-300">Evidence URL</label>
						<input
							value={form.evidence_url}
							onChange={(e) => setField("evidence_url", e.target.value)}
							className={inputClass}
							placeholder="https://github.com/me/project"
						/>
					</div>
					<div className="sm:col-span-2">
						<label className="text-sm text-slate-600 dark:text-slate-300">Evidence note</label>
						<textarea
							value={form.evidence_note}
							onChange={(e) => setField("evidence_note", e.target.value)}
							className={inputClass}
							rows={3}
							placeholder="What did you build / how does this prove the skill?"
						/>
					</div>
				</div>
				<button
					type="submit"
					disabled={submitting}
					className="mt-5 rounded-lg bg-gradient-to-r from-indigo-500 to-violet-500 px-5 py-2.5 text-sm font-medium text-white transition hover:opacity-90 disabled:opacity-50"
				>
					{submitting ? "Claiming..." : "Claim skill"}
				</button>
			</form>

			{/* Skills list */}
			<div className="mt-8">
				{loading ? (
					<p className="text-slate-500 dark:text-slate-400">Loading your skills...</p>
				) : skills.length === 0 ? (
					<p className="text-slate-500 dark:text-slate-400">
						No skills claimed yet. Add your first one above.
					</p>
				) : (
					<div className="space-y-3">
						{skills.map((skill) => (
							<div
								key={skill.id}
								className="rounded-xl border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-900 p-4"
							>
								<div className="flex flex-wrap items-center justify-between gap-2">
									<div className="flex items-center gap-2">
										<span className="font-medium">{skill.name}</span>
										<span
											className={`rounded-full px-2 py-0.5 text-xs capitalize ${STATUS_STYLES[skill.status]}`}
										>
											{skill.status}
										</span>
										<span className="text-xs text-slate-500 dark:text-slate-400">
											AI score:{" "}
											{skill.ai_score != null
												? skill.ai_score.toFixed(2)
												: "pending"}
										</span>
									</div>
									<button
										onClick={() => remove(skill)}
										className="rounded-lg border border-slate-300 dark:border-white/15 px-3 py-1 text-xs transition hover:bg-slate-100 dark:hover:bg-white/10"
									>
										Delete
									</button>
								</div>

								{skill.evidence_note && (
									<p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
										{skill.evidence_note}
									</p>
								)}
								{skill.evidence_url && (
									<a
										href={skill.evidence_url}
										target="_blank"
										rel="noreferrer"
										className="mt-1 inline-block text-xs text-indigo-600 dark:text-indigo-300 underline"
									>
										{skill.evidence_url}
									</a>
								)}
								{skill.review_note && (
									<p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
										Mentor note: {skill.review_note}
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
