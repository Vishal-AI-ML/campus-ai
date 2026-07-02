/**
 * Campus AI - Student Projects page (verified-data moat, per-member credit).
 *
 * Place this file at: src/app/dashboard/projects/page.tsx
 *
 * A student adds a project with proof links. For a group project they list
 * teammates (by student id) + each one's contribution. Every member starts
 * `pending`; a mentor verifies/flags each contribution individually, so only
 * verified contributions count toward resume / placement eligibility.
 *
 * Backend endpoints:
 *   POST   /projects     body: { title, description?, tech_stack?, repo_url?,
 *                                demo_url?, is_group, members?: [{student_id,
 *                                contribution?}] }
 *   GET    /projects/me
 *   DELETE /projects/{id}   (owner only)
 */

"use client"

import { useEffect, useState } from "react"
import { api, ApiError } from "@/lib/api"

type MemberStatus = "pending" | "verified" | "flagged"

type ProjectMember = {
	id: number
	project_id: number
	student_id: number
	contribution: string | null
	status: MemberStatus
	ai_score: number | null
	review_note: string | null
}

type Project = {
	id: number
	owner_id: number
	title: string
	description: string | null
	tech_stack: string | null
	repo_url: string | null
	demo_url: string | null
	is_group: boolean
	members: ProjectMember[]
}

type ProjectForm = {
	title: string
	description: string
	tech_stack: string
	repo_url: string
	demo_url: string
	is_group: boolean
}

type TeamMate = { student_id: string; contribution: string }

const EMPTY_FORM: ProjectForm = {
	title: "",
	description: "",
	tech_stack: "",
	repo_url: "",
	demo_url: "",
	is_group: false,
}

const STATUS_STYLES: Record<MemberStatus, string> = {
	pending: "bg-amber-500/15 text-amber-600 dark:text-amber-300",
	verified: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-300",
	flagged: "bg-red-500/15 text-red-300",
}

export default function ProjectsPage() {
	const [projects, setProjects] = useState<Project[]>([])
	const [loading, setLoading] = useState(true)
	const [submitting, setSubmitting] = useState(false)
	const [error, setError] = useState<string | null>(null)
	const [form, setForm] = useState<ProjectForm>(EMPTY_FORM)
	const [team, setTeam] = useState<TeamMate[]>([])

	async function load() {
		setLoading(true)
		setError(null)
		try {
			setProjects(await api.get<Project[]>("/projects/me"))
		} catch (err) {
			setError(
				err instanceof ApiError ? err.message : "Could not load projects.",
			)
		} finally {
			setLoading(false)
		}
	}

	useEffect(() => {
		load()
	}, [])

	function setField(key: keyof ProjectForm, val: string | boolean) {
		setForm((prev) => ({ ...prev, [key]: val }))
	}

	function addMate() {
		setTeam((prev) => [...prev, { student_id: "", contribution: "" }])
	}

	function setMate(index: number, key: keyof TeamMate, val: string) {
		setTeam((prev) =>
			prev.map((mate, i) => (i === index ? { ...mate, [key]: val } : mate)),
		)
	}

	function removeMate(index: number) {
		setTeam((prev) => prev.filter((_, i) => i !== index))
	}

	async function handleSubmit(e: React.FormEvent) {
		e.preventDefault()
		setError(null)
		setSubmitting(true)
		try {
			const payload: Record<string, unknown> = {
				title: form.title.trim(),
				is_group: form.is_group,
			}
			if (form.description.trim()) payload.description = form.description.trim()
			if (form.tech_stack.trim()) payload.tech_stack = form.tech_stack.trim()
			if (form.repo_url.trim()) payload.repo_url = form.repo_url.trim()
			if (form.demo_url.trim()) payload.demo_url = form.demo_url.trim()

			if (form.is_group) {
				const mates = team
					.filter((mate) => mate.student_id.trim())
					.map((mate) => ({
						student_id: Number(mate.student_id),
						contribution: mate.contribution.trim() || null,
					}))
				if (mates.some((mate) => Number.isNaN(mate.student_id))) {
					throw new ApiError(0, "Teammate student id must be a number.")
				}
				payload.members = mates
			}

			await api.post<Project>("/projects", payload)
			setForm(EMPTY_FORM)
			setTeam([])
			await load()
		} catch (err) {
			setError(
				err instanceof ApiError ? err.message : "Could not create the project.",
			)
		} finally {
			setSubmitting(false)
		}
	}

	async function remove(project: Project) {
		setError(null)
		try {
			await api.delete(`/projects/${project.id}`)
			await load()
		} catch (err) {
			setError(
				err instanceof ApiError
					? err.message
					: "Could not delete the project (only the owner can).",
			)
		}
	}

	const inputClass =
		"mt-1 w-full rounded-lg border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-900 px-3 py-2 text-sm outline-none focus:border-indigo-400"

	return (
		<div>
			<h2 className="text-2xl font-bold">My Projects</h2>
			<p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
				Add a project with proof links. A mentor verifies each contribution —
				only verified work counts toward your resume and eligibility.
			</p>

			{error && (
				<p className="mt-4 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">
					{error}
				</p>
			)}

			{/* Create form */}
			<form
				onSubmit={handleSubmit}
				className="mt-6 rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-900 p-6"
			>
				<div className="grid gap-4 sm:grid-cols-2">
					<div className="sm:col-span-2">
						<label className="text-sm text-slate-600 dark:text-slate-300">Title *</label>
						<input
							required
							value={form.title}
							onChange={(e) => setField("title", e.target.value)}
							className={inputClass}
							placeholder="Campus Attendance API"
						/>
					</div>
					<div className="sm:col-span-2">
						<label className="text-sm text-slate-600 dark:text-slate-300">Description</label>
						<textarea
							value={form.description}
							onChange={(e) => setField("description", e.target.value)}
							className={inputClass}
							rows={3}
							placeholder="What does this project do?"
						/>
					</div>
					<div>
						<label className="text-sm text-slate-600 dark:text-slate-300">Tech stack</label>
						<input
							value={form.tech_stack}
							onChange={(e) => setField("tech_stack", e.target.value)}
							className={inputClass}
							placeholder="FastAPI, PostgreSQL, Docker"
						/>
					</div>
					<div>
						<label className="text-sm text-slate-600 dark:text-slate-300">Repo URL</label>
						<input
							value={form.repo_url}
							onChange={(e) => setField("repo_url", e.target.value)}
							className={inputClass}
							placeholder="https://github.com/me/campus-api"
						/>
					</div>
					<div>
						<label className="text-sm text-slate-600 dark:text-slate-300">Demo URL</label>
						<input
							value={form.demo_url}
							onChange={(e) => setField("demo_url", e.target.value)}
							className={inputClass}
							placeholder="https://my-demo.vercel.app"
						/>
					</div>
					<div className="flex items-center gap-2 sm:col-span-2">
						<input
							id="is_group"
							type="checkbox"
							checked={form.is_group}
							onChange={(e) => setField("is_group", e.target.checked)}
							className="h-4 w-4"
						/>
						<label htmlFor="is_group" className="text-sm text-slate-600 dark:text-slate-300">
							This is a group project
						</label>
					</div>
				</div>

				{/* Teammates (group only) */}
				{form.is_group && (
					<div className="mt-5 rounded-xl border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-900 p-4">
						<div className="flex items-center justify-between">
							<p className="text-sm font-medium text-slate-700 dark:text-slate-200">
								Teammates
							</p>
							<button
								type="button"
								onClick={addMate}
								className="rounded-lg border border-slate-300 dark:border-white/15 px-3 py-1 text-xs transition hover:bg-slate-100 dark:hover:bg-white/10"
							>
								+ Add teammate
							</button>
						</div>
						<p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
							You are added automatically as the owner. Add teammates by their
							student id.
						</p>
						{team.length === 0 ? (
							<p className="mt-3 text-xs text-slate-500 dark:text-slate-400">
								No teammates added yet.
							</p>
						) : (
							<div className="mt-3 space-y-2">
								{team.map((mate, index) => (
									<div key={index} className="flex flex-wrap gap-2">
										<input
											value={mate.student_id}
											onChange={(e) =>
												setMate(index, "student_id", e.target.value)
											}
											className="w-28 rounded-lg border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-900 px-3 py-2 text-sm outline-none focus:border-indigo-400"
											placeholder="Student id"
										/>
										<input
											value={mate.contribution}
											onChange={(e) =>
												setMate(index, "contribution", e.target.value)
											}
											className="flex-1 rounded-lg border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-900 px-3 py-2 text-sm outline-none focus:border-indigo-400"
											placeholder="What did they build?"
										/>
										<button
											type="button"
											onClick={() => removeMate(index)}
											className="rounded-lg border border-slate-300 dark:border-white/15 px-3 py-2 text-xs transition hover:bg-slate-100 dark:hover:bg-white/10"
										>
											Remove
										</button>
									</div>
								))}
							</div>
						)}
					</div>
				)}

				<button
					type="submit"
					disabled={submitting}
					className="mt-5 rounded-lg bg-gradient-to-r from-indigo-500 to-violet-500 px-5 py-2.5 text-sm font-medium text-white transition hover:opacity-90 disabled:opacity-50"
				>
					{submitting ? "Creating..." : "Add project"}
				</button>
			</form>

			{/* Projects list */}
			<div className="mt-8">
				{loading ? (
					<p className="text-slate-500 dark:text-slate-400">Loading your projects...</p>
				) : projects.length === 0 ? (
					<p className="text-slate-500 dark:text-slate-400">
						No projects yet. Add your first one above.
					</p>
				) : (
					<div className="space-y-4">
						{projects.map((project) => (
							<div
								key={project.id}
								className="rounded-xl border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-900 p-4"
							>
								<div className="flex flex-wrap items-center justify-between gap-2">
									<div className="flex items-center gap-2">
										<span className="font-medium">{project.title}</span>
										{project.is_group && (
											<span className="rounded-full bg-indigo-500/15 px-2 py-0.5 text-xs text-indigo-600 dark:text-indigo-300">
												Group
											</span>
										)}
									</div>
									<button
										onClick={() => remove(project)}
										className="rounded-lg border border-slate-300 dark:border-white/15 px-3 py-1 text-xs transition hover:bg-slate-100 dark:hover:bg-white/10"
									>
										Delete
									</button>
								</div>

								{project.description && (
									<p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
										{project.description}
									</p>
								)}
								{project.tech_stack && (
									<p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
										{project.tech_stack}
									</p>
								)}
								<div className="mt-2 flex flex-wrap gap-3">
									{project.repo_url && (
										<a
											href={project.repo_url}
											target="_blank"
											rel="noreferrer"
											className="text-xs text-indigo-600 dark:text-indigo-300 underline"
										>
											Repo
										</a>
									)}
									{project.demo_url && (
										<a
											href={project.demo_url}
											target="_blank"
											rel="noreferrer"
											className="text-xs text-indigo-600 dark:text-indigo-300 underline"
										>
											Demo
										</a>
									)}
								</div>

								{/* Per-member verification */}
								<div className="mt-3 space-y-2 border-t border-slate-200 dark:border-white/10 pt-3">
									{project.members.map((member) => (
										<div
											key={member.id}
											className="flex flex-wrap items-center gap-2 text-sm"
										>
											<span className="text-slate-600 dark:text-slate-300">
												Student #{member.student_id}
											</span>
											<span
												className={`rounded-full px-2 py-0.5 text-xs capitalize ${STATUS_STYLES[member.status]}`}
											>
												{member.status}
											</span>
											<span className="text-xs text-slate-500 dark:text-slate-400">
												AI score:{" "}
												{member.ai_score != null
													? member.ai_score.toFixed(2)
													: "pending"}
											</span>
											{member.contribution && (
												<span className="text-xs text-slate-500 dark:text-slate-400">
													— {member.contribution}
												</span>
											)}
											{member.review_note && (
												<span className="w-full text-xs text-slate-500 dark:text-slate-400">
													Mentor note: {member.review_note}
												</span>
											)}
										</div>
									))}
								</div>
							</div>
						))}
					</div>
				)}
			</div>
		</div>
	)
}
