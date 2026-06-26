/**
 * Campus AI - lead-capture contact form (client component).
 *
 * Place this file at: src/components/ContactForm.tsx
 *
 * Submits to POST /leads (built in step 5.5). Until that backend route exists,
 * submit will show a friendly error; once it's live, this works as-is.
 */

"use client"

import { useState } from "react"
import { api, ApiError } from "@/lib/api"

type LeadForm = {
	name: string
	email: string
	institute: string
	role: string
	message: string
}

const EMPTY: LeadForm = {
	name: "",
	email: "",
	institute: "",
	role: "Administrator",
	message: "",
}

const ROLE_OPTIONS = [
	"Administrator",
	"Placement Officer (TPO)",
	"Teacher",
	"Student",
	"Other",
]

export default function ContactForm() {
	const [form, setForm] = useState<LeadForm>(EMPTY)
	const [submitting, setSubmitting] = useState(false)
	const [submitted, setSubmitted] = useState(false)
	const [error, setError] = useState<string | null>(null)

	function setField(key: keyof LeadForm, val: string) {
		setForm((prev) => ({ ...prev, [key]: val }))
	}

	async function handleSubmit(e: React.FormEvent) {
		e.preventDefault()
		setError(null)
		setSubmitting(true)
		try {
			await api.post("/leads", {
				name: form.name.trim(),
				email: form.email.trim(),
				institute: form.institute.trim() || null,
				role: form.role,
				message: form.message.trim(),
			})
			setSubmitted(true)
			setForm(EMPTY)
		} catch (err) {
			setError(
				err instanceof ApiError
					? err.message
					: "Could not submit right now. Please try again later.",
			)
		} finally {
			setSubmitting(false)
		}
	}

	const inputClass =
		"mt-1 w-full rounded-lg border border-white/10 bg-slate-900 px-3 py-2 text-sm outline-none focus:border-indigo-400"

	if (submitted) {
		return (
			<div className="rounded-2xl border border-emerald-500/30 bg-emerald-500/10 p-8 text-center">
				<div className="text-3xl">✓</div>
				<h3 className="mt-3 text-xl font-semibold">Thanks for reaching out!</h3>
				<p className="mt-2 text-sm text-slate-300">
					Our team will get back to you shortly.
				</p>
				<button
					onClick={() => setSubmitted(false)}
					className="mt-5 rounded-lg border border-white/15 px-4 py-2 text-sm transition hover:bg-white/5"
				>
					Send another
				</button>
			</div>
		)
	}

	return (
		<form
			onSubmit={handleSubmit}
			className="rounded-2xl border border-white/10 bg-white/5 p-6"
		>
			{error && (
				<p className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">
					{error}
				</p>
			)}
			<div className="grid gap-4 sm:grid-cols-2">
				<div>
					<label className="text-sm text-slate-300">Name *</label>
					<input
						required
						value={form.name}
						onChange={(e) => setField("name", e.target.value)}
						className={inputClass}
						placeholder="Your name"
					/>
				</div>
				<div>
					<label className="text-sm text-slate-300">Email *</label>
					<input
						required
						type="email"
						value={form.email}
						onChange={(e) => setField("email", e.target.value)}
						className={inputClass}
						placeholder="you@institute.edu"
					/>
				</div>
				<div>
					<label className="text-sm text-slate-300">Institute</label>
					<input
						value={form.institute}
						onChange={(e) => setField("institute", e.target.value)}
						className={inputClass}
						placeholder="Your college / university"
					/>
				</div>
				<div>
					<label className="text-sm text-slate-300">I am a</label>
					<select
						value={form.role}
						onChange={(e) => setField("role", e.target.value)}
						className={inputClass}
					>
						{ROLE_OPTIONS.map((option) => (
							<option key={option} value={option}>
								{option}
							</option>
						))}
					</select>
				</div>
				<div className="sm:col-span-2">
					<label className="text-sm text-slate-300">Message *</label>
					<textarea
						required
						value={form.message}
						onChange={(e) => setField("message", e.target.value)}
						className={inputClass}
						rows={4}
						placeholder="Tell us about your institute and what you're looking for."
					/>
				</div>
			</div>
			<button
				type="submit"
				disabled={submitting}
				className="mt-5 rounded-lg bg-gradient-to-r from-indigo-500 to-violet-500 px-6 py-2.5 text-sm font-medium text-white transition hover:opacity-90 disabled:opacity-50"
			>
				{submitting ? "Sending..." : "Send message"}
			</button>
		</form>
	)
}
