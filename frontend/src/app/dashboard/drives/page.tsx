/**
 * Campus AI - TPO Placement Drives page.
 *
 * Place this file at: src/app/dashboard/drives/page.tsx
 *
 * Lists all placement drives, lets the TPO post a new drive (with verified-data
 * eligibility criteria), and open/close a drive. Uses the backend endpoints:
 *   GET   /drives                 (list, TPO/admin)
 *   POST  /drives                 (create, TPO)
 *   PATCH /drives/{id}/status     (open/close, TPO)
 */

"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { api, ApiError } from "@/lib/api"

type Drive = {
	id: number
	company_name: string
	role_title: string
	description: string | null
	location: string | null
	package_lpa: number | null
	min_cgpa: number
	min_attendance: number
	min_verified_projects: number
	required_skills: string | null
	is_open: boolean
	deadline: string | null
}

// String-based form state (inputs are strings; converted on submit).
type DriveForm = {
	company_name: string
	role_title: string
	description: string
	location: string
	package_lpa: string
	min_cgpa: string
	min_attendance: string
	min_verified_projects: string
	required_skills: string
	deadline: string
}

const EMPTY_FORM: DriveForm = {
	company_name: "",
	role_title: "",
	description: "",
	location: "",
	package_lpa: "",
	min_cgpa: "0",
	min_attendance: "0",
	min_verified_projects: "0",
	required_skills: "",
	deadline: "",
}

export default function DrivesPage() {
	const [drives, setDrives] = useState<Drive[]>([])
	const [loading, setLoading] = useState(true)
	const [error, setError] = useState<string | null>(null)
	const [showForm, setShowForm] = useState(false)
	const [submitting, setSubmitting] = useState(false)
	const [form, setForm] = useState<DriveForm>(EMPTY_FORM)

	async function load() {
		setLoading(true)
		setError(null)
		try {
			setDrives(await api.get<Drive[]>("/drives"))
		} catch (err) {
			setError(
				err instanceof ApiError ? err.message : "Could not load drives.",
			)
		} finally {
			setLoading(false)
		}
	}

	useEffect(() => {
		load()
	}, [])

	// Update a single field of the form.
	function setField(key: keyof DriveForm, val: string) {
		setForm((prev) => ({ ...prev, [key]: val }))
	}

	async function handleSubmit(e: React.FormEvent) {
		e.preventDefault()
		setError(null)
		setSubmitting(true)
		try {
			const payload: Record<string, unknown> = {
				company_name: form.company_name.trim(),
				role_title: form.role_title.trim(),
				min_cgpa: Number(form.min_cgpa) || 0,
				min_attendance: Number(form.min_attendance) || 0,
				min_verified_projects: Number(form.min_verified_projects) || 0,
			}
			if (form.description.trim()) payload.description = form.description.trim()
			if (form.location.trim()) payload.location = form.location.trim()
			if (form.package_lpa.trim()) payload.package_lpa = Number(form.package_lpa)
			if (form.required_skills.trim())
				payload.required_skills = form.required_skills.trim()
			if (form.deadline) payload.deadline = form.deadline

			await api.post<Drive>("/drives", payload)
			setForm(EMPTY_FORM)
			setShowForm(false)
			await load()
		} catch (err) {
			setError(
				err instanceof ApiError ? err.message : "Could not create the drive.",
			)
		} finally {
			setSubmitting(false)
		}
	}

	async function toggleOpen(drive: Drive) {
		setError(null)
		try {
			await api.patch<Drive>(`/drives/${drive.id}/status`, {
				is_open: !drive.is_open,
			})
			await load()
		} catch (err) {
			setError(
				err instanceof ApiError ? err.message : "Could not update the drive.",
			)
		}
	}

	const inputClass =
		"mt-1 w-full rounded-lg border border-white/10 bg-slate-900 px-3 py-2 text-sm outline-none focus:border-indigo-400"

	return (
		<div>
			<div className="flex items-center justify-between">
				<div>
					<h2 className="text-2xl font-bold">Placement Drives</h2>
					<p className="mt-1 text-sm text-slate-400">
						Post drives and check who qualifies on verified data.
					</p>
				</div>
				<button
					onClick={() => setShowForm((v) => !v)}
					className="rounded-lg bg-gradient-to-r from-indigo-500 to-violet-500 px-4 py-2 text-sm font-medium text-white transition hover:opacity-90"
				>
					{showForm ? "Close" : "+ New Drive"}
				</button>
			</div>

			{error && (
				<p className="mt-4 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">
					{error}
				</p>
			)}

			{/* Create form */}
			{showForm && (
				<form
					onSubmit={handleSubmit}
					className="mt-6 rounded-2xl border border-white/10 bg-white/5 p-6"
				>
					<div className="grid gap-4 sm:grid-cols-2">
						<div>
							<label className="text-sm text-slate-300">Company *</label>
							<input
								required
								value={form.company_name}
								onChange={(e) => setField("company_name", e.target.value)}
								className={inputClass}
								placeholder="Acme Corp"
							/>
						</div>
						<div>
							<label className="text-sm text-slate-300">Role title *</label>
							<input
								required
								value={form.role_title}
								onChange={(e) => setField("role_title", e.target.value)}
								className={inputClass}
								placeholder="Backend Engineer"
							/>
						</div>
						<div>
							<label className="text-sm text-slate-300">Location</label>
							<input
								value={form.location}
								onChange={(e) => setField("location", e.target.value)}
								className={inputClass}
								placeholder="Bangalore"
							/>
						</div>
						<div>
							<label className="text-sm text-slate-300">Package (LPA)</label>
							<input
								type="number"
								step="0.1"
								value={form.package_lpa}
								onChange={(e) => setField("package_lpa", e.target.value)}
								className={inputClass}
								placeholder="12"
							/>
						</div>
						<div>
							<label className="text-sm text-slate-300">Min CGPA</label>
							<input
								type="number"
								step="0.1"
								value={form.min_cgpa}
								onChange={(e) => setField("min_cgpa", e.target.value)}
								className={inputClass}
							/>
						</div>
						<div>
							<label className="text-sm text-slate-300">Min attendance %</label>
							<input
								type="number"
								step="1"
								value={form.min_attendance}
								onChange={(e) => setField("min_attendance", e.target.value)}
								className={inputClass}
							/>
						</div>
						<div>
							<label className="text-sm text-slate-300">Min verified projects</label>
							<input
								type="number"
								step="1"
								value={form.min_verified_projects}
								onChange={(e) =>
									setField("min_verified_projects", e.target.value)
								}
								className={inputClass}
							/>
						</div>
						<div>
							<label className="text-sm text-slate-300">Deadline</label>
							<input
								type="date"
								value={form.deadline}
								onChange={(e) => setField("deadline", e.target.value)}
								className={inputClass}
							/>
						</div>
						<div className="sm:col-span-2">
							<label className="text-sm text-slate-300">
								Required skills (comma-separated)
							</label>
							<input
								value={form.required_skills}
								onChange={(e) => setField("required_skills", e.target.value)}
								className={inputClass}
								placeholder="FastAPI, SQL, Docker"
							/>
						</div>
						<div className="sm:col-span-2">
							<label className="text-sm text-slate-300">Description</label>
							<textarea
								value={form.description}
								onChange={(e) => setField("description", e.target.value)}
								className={inputClass}
								rows={3}
							/>
						</div>
					</div>
					<button
						type="submit"
						disabled={submitting}
						className="mt-5 rounded-lg bg-gradient-to-r from-indigo-500 to-violet-500 px-5 py-2.5 text-sm font-medium text-white transition hover:opacity-90 disabled:opacity-50"
					>
						{submitting ? "Posting..." : "Post drive"}
					</button>
				</form>
			)}

			{/* Drives list */}
			<div className="mt-8">
				{loading ? (
					<p className="text-slate-400">Loading drives...</p>
				) : drives.length === 0 ? (
					<p className="text-slate-400">No drives yet. Post your first one.</p>
				) : (
					<div className="space-y-4">
						{drives.map((drive) => (
							<div
								key={drive.id}
								className="rounded-2xl border border-white/10 bg-white/5 p-5"
							>
								<div className="flex flex-wrap items-start justify-between gap-3">
									<div>
										<div className="flex items-center gap-2">
											<h3 className="text-lg font-semibold">
												{drive.company_name}
											</h3>
											<span
												className={`rounded-full px-2 py-0.5 text-xs ${
													drive.is_open
													? "bg-emerald-500/15 text-emerald-300"
													: "bg-slate-500/15 text-slate-400"
												}`}
											>
												{drive.is_open ? "Open" : "Closed"}
											</span>
										</div>
										<p className="text-sm text-slate-300">
											{drive.role_title}
											{drive.location ? ` \u00B7 ${drive.location}` : ""}
											{drive.package_lpa != null
												? ` \u00B7 ${drive.package_lpa} LPA`
												: ""}
										</p>
									</div>
									<div className="flex gap-2">
										<button
											onClick={() => toggleOpen(drive)}
											className="rounded-lg border border-white/15 px-3 py-1.5 text-sm transition hover:bg-white/5"
										>
											{drive.is_open ? "Close" : "Open"}
										</button>
										<Link
											href={`/dashboard/drives/${drive.id}`}
											className="rounded-lg bg-white/10 px-3 py-1.5 text-sm transition hover:bg-white/15"
										>
											Eligibility &amp; applicants →
										</Link>
									</div>
								</div>

								<div className="mt-4 flex flex-wrap gap-2 text-xs text-slate-300">
									<span className="rounded-md bg-white/5 px-2 py-1">
										Min CGPA: {drive.min_cgpa}
									</span>
									<span className="rounded-md bg-white/5 px-2 py-1">
										Min attendance: {drive.min_attendance}%
									</span>
									<span className="rounded-md bg-white/5 px-2 py-1">
										Min projects: {drive.min_verified_projects}
									</span>
									{drive.required_skills && (
										<span className="rounded-md bg-white/5 px-2 py-1">
											Skills: {drive.required_skills}
										</span>
									)}
									{drive.deadline && (
										<span className="rounded-md bg-white/5 px-2 py-1">
											Deadline: {drive.deadline}
										</span>
									)}
								</div>
							</div>
						))}
					</div>
				)}
			</div>
		</div>
	)
}
