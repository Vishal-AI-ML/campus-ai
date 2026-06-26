/**
 * Campus AI - Teacher/Mentor Verification Queue.
 *
 * Place this file at: src/app/dashboard/verify/page.tsx
 *
 * The mentor reviews pending skill claims and project contributions, sees the
 * AI advisory score + proof, and verifies or flags each one (with an optional
 * review note). Only verified items count toward resume / eligibility, so this
 * is the gate that makes the 'verified data moat' real.
 *
 * Backend endpoints:
 *   GET   /skills/queue?status_filter=pending
 *   PATCH /skills/{skill_id}/decision            body: { status, review_note? }
 *   GET   /projects/queue?status_filter=pending
 *   PATCH /projects/members/{member_id}/decision body: { status, review_note? }
 */

"use client"

import { useCallback, useEffect, useState } from "react"
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

type MemberQueue = {
	member_id: number
	project_id: number
	project_title: string
	repo_url: string | null
	student_id: number
	contribution: string | null
	status: SkillStatus
}

export default function VerifyPage() {
	const [tab, setTab] = useState<"skills" | "projects">("skills")
	const [skills, setSkills] = useState<Skill[]>([])
	const [members, setMembers] = useState<MemberQueue[]>([])
	const [notes, setNotes] = useState<Record<string, string>>({})
	const [loading, setLoading] = useState(true)
	const [busyKey, setBusyKey] = useState<string | null>(null)
	const [error, setError] = useState<string | null>(null)

	const loadSkills = useCallback(async () => {
		setLoading(true)
		setError(null)
		try {
			setSkills(await api.get<Skill[]>("/skills/queue"))
		} catch (err) {
			setError(
				err instanceof ApiError ? err.message : "Could not load skill queue.",
			)
		} finally {
			setLoading(false)
		}
	}, [])

	const loadProjects = useCallback(async () => {
		setLoading(true)
		setError(null)
		try {
			setMembers(await api.get<MemberQueue[]>("/projects/queue"))
		} catch (err) {
			setError(
				err instanceof ApiError
					? err.message
					: "Could not load project queue.",
			)
		} finally {
			setLoading(false)
		}
	}, [])

	useEffect(() => {
		if (tab === "skills") loadSkills()
		else loadProjects()
	}, [tab, loadSkills, loadProjects])

	function setNote(key: string, val: string) {
		setNotes((prev) => ({ ...prev, [key]: val }))
	}

	async function decideSkill(skill: Skill, status: "verified" | "flagged") {
		const key = `s${skill.id}`
		setBusyKey(key)
		setError(null)
		try {
			const body: Record<string, unknown> = { status }
			const note = (notes[key] ?? "").trim()
			if (note) body.review_note = note
			await api.patch(`/skills/${skill.id}/decision`, body)
			await loadSkills()
		} catch (err) {
			setError(
				err instanceof ApiError ? err.message : "Could not save decision.",
			)
		} finally {
			setBusyKey(null)
		}
	}

	async function decideMember(
		member: MemberQueue,
		status: "verified" | "flagged",
	) {
		const key = `p${member.member_id}`
		setBusyKey(key)
		setError(null)
		try {
			const body: Record<string, unknown> = { status }
			const note = (notes[key] ?? "").trim()
			if (note) body.review_note = note
			await api.patch(`/projects/members/${member.member_id}/decision`, body)
			await loadProjects()
		} catch (err) {
			setError(
				err instanceof ApiError ? err.message : "Could not save decision.",
			)
		} finally {
			setBusyKey(null)
		}
	}

	const tabClass = (active: boolean) =>
		`rounded-lg px-4 py-2 text-sm transition ${
			active ? "bg-indigo-500/15 text-white" : "text-slate-300 hover:bg-white/5"
		}`

	const noteClass =
		"mt-3 w-full rounded-lg border border-white/10 bg-slate-900 px-3 py-2 text-sm outline-none focus:border-indigo-400"

	return (
		<div>
			<h2 className="text-2xl font-bold">Verification Queue</h2>
			<p className="mt-1 text-sm text-slate-400">
				Review pending claims. Only what you verify counts toward resumes and
				placement eligibility.
			</p>

			<div className="mt-6 flex gap-2">
				<button
					onClick={() => setTab("skills")}
					className={tabClass(tab === "skills")}
				>
					Skills
				</button>
				<button
					onClick={() => setTab("projects")}
					className={tabClass(tab === "projects")}
				>
					Projects
				</button>
			</div>

			{error && (
				<p className="mt-4 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">
					{error}
				</p>
			)}

			{/* Skills queue */}
			{tab === "skills" && (
				<div className="mt-6">
					{loading ? (
						<p className="text-slate-400">Loading queue...</p>
					) : skills.length === 0 ? (
						<p className="text-slate-400">No pending skill claims. All clear.</p>
					) : (
						<div className="space-y-3">
							{skills.map((skill) => {
								const key = `s${skill.id}`
								return (
									<div
										key={skill.id}
										className="rounded-xl border border-white/10 bg-white/5 p-4"
									>
										<div className="flex flex-wrap items-center justify-between gap-2">
											<span className="font-medium">{skill.name}</span>
											<span className="text-xs text-slate-400">
												Student #{skill.student_id} · AI score:{" "}
												{skill.ai_score != null
													? skill.ai_score.toFixed(2)
													: "pending"}
											</span>
										</div>
										{skill.evidence_note && (
											<p className="mt-2 text-sm text-slate-300">
												{skill.evidence_note}
											</p>
										)}
										{skill.evidence_url && (
											<a
												href={skill.evidence_url}
												target="_blank"
												rel="noreferrer"
												className="mt-1 inline-block text-xs text-indigo-300 underline"
											>
												{skill.evidence_url}
											</a>
										)}
										<input
											value={notes[key] ?? ""}
											onChange={(e) => setNote(key, e.target.value)}
											className={noteClass}
											placeholder="Review note (optional)"
										/>
										<div className="mt-3 flex gap-2">
											<button
												onClick={() => decideSkill(skill, "verified")}
												disabled={busyKey === key}
												className="rounded-lg border border-emerald-400/30 px-3 py-1.5 text-sm text-emerald-300 transition hover:bg-emerald-400/10 disabled:opacity-40"
											>
												Verify
											</button>
											<button
												onClick={() => decideSkill(skill, "flagged")}
												disabled={busyKey === key}
												className="rounded-lg border border-red-400/30 px-3 py-1.5 text-sm text-red-300 transition hover:bg-red-400/10 disabled:opacity-40"
											>
												Flag
											</button>
										</div>
									</div>
								)
							})}
						</div>
					)}
				</div>
			)}

			{/* Projects queue */}
			{tab === "projects" && (
				<div className="mt-6">
					{loading ? (
						<p className="text-slate-400">Loading queue...</p>
					) : members.length === 0 ? (
						<p className="text-slate-400">
							No pending contributions. All clear.
						</p>
					) : (
						<div className="space-y-3">
							{members.map((member) => {
								const key = `p${member.member_id}`
								return (
									<div
										key={member.member_id}
										className="rounded-xl border border-white/10 bg-white/5 p-4"
									>
										<div className="flex flex-wrap items-center justify-between gap-2">
											<span className="font-medium">
												{member.project_title}
											</span>
											<span className="text-xs text-slate-400">
												Student #{member.student_id}
											</span>
										</div>
										{member.contribution && (
											<p className="mt-2 text-sm text-slate-300">
												Contribution: {member.contribution}
											</p>
										)}
										{member.repo_url && (
											<a
												href={member.repo_url}
												target="_blank"
												rel="noreferrer"
												className="mt-1 inline-block text-xs text-indigo-300 underline"
											>
												{member.repo_url}
											</a>
										)}
										<input
											value={notes[key] ?? ""}
											onChange={(e) => setNote(key, e.target.value)}
											className={noteClass}
											placeholder="Review note (optional)"
										/>
										<div className="mt-3 flex gap-2">
											<button
												onClick={() => decideMember(member, "verified")}
												disabled={busyKey === key}
												className="rounded-lg border border-emerald-400/30 px-3 py-1.5 text-sm text-emerald-300 transition hover:bg-emerald-400/10 disabled:opacity-40"
											>
												Verify
											</button>
											<button
												onClick={() => decideMember(member, "flagged")}
												disabled={busyKey === key}
												className="rounded-lg border border-red-400/30 px-3 py-1.5 text-sm text-red-300 transition hover:bg-red-400/10 disabled:opacity-40"
											>
												Flag
											</button>
										</div>
									</div>
								)
							})}
						</div>
					)}
				</div>
			)}
		</div>
	)
}
