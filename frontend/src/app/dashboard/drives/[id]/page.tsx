/**
 * Campus AI - TPO drive detail page (eligibility engine + applicants).
 *
 * Place this file at: src/app/dashboard/drives/[id]/page.tsx
 *
 * Two tabs:
 *   - Eligibility: runs the verified-data engine across all students and shows
 *     each verdict with explainable per-criterion reasons.
 *   - Applicants: lists who applied (with a verified snapshot) and lets the TPO
 *     shortlist / select / reject.
 *
 * Backend endpoints:
 *   GET   /drives/{id}
 *   GET   /drives/{id}/eligibility?eligible_only=<bool>
 *   GET   /drives/{id}/applications
 *   PATCH /drives/applications/{application_id}/status   body: { status, note? }
 */

"use client"

import { useCallback, useEffect, useState } from "react"
import Link from "next/link"
import { useParams } from "next/navigation"
import { api, ApiError } from "@/lib/api"

type Drive = {
	id: number
	company_name: string
	role_title: string
	location: string | null
	package_lpa: number | null
	min_cgpa: number
	min_attendance: number
	min_verified_projects: number
	required_skills: string | null
	is_open: boolean
	deadline: string | null
}

type Reason = { criterion: string; passed: boolean; detail: string }

type Eligibility = {
	student_id: number
	full_name: string
	eligible: boolean
	cgpa: number
	attendance: number
	verified_skills: number
	verified_projects: number
	reasons: Reason[]
}

type AppStatus = "applied" | "shortlisted" | "selected" | "rejected"

type Applicant = {
	application_id: number
	student_id: number
	full_name: string
	status: AppStatus
	eligible: boolean
	cgpa: number
	attendance: number
	verified_skills: number
	verified_projects: number
	note: string | null
}

const STATUS_STYLES: Record<AppStatus, string> = {
	applied: "bg-slate-500/15 text-slate-600 dark:text-slate-300",
	shortlisted: "bg-amber-500/15 text-amber-600 dark:text-amber-300",
	selected: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-300",
	rejected: "bg-red-500/15 text-red-300",
}

export default function DriveDetailPage() {
	const params = useParams<{ id: string }>()
	const driveId = params.id

	const [drive, setDrive] = useState<Drive | null>(null)
	const [tab, setTab] = useState<"eligibility" | "applicants">("eligibility")
	const [eligibility, setEligibility] = useState<Eligibility[]>([])
	const [eligibleOnly, setEligibleOnly] = useState(false)
	const [applicants, setApplicants] = useState<Applicant[]>([])
	const [loading, setLoading] = useState(true)
	const [error, setError] = useState<string | null>(null)

	const loadDrive = useCallback(async () => {
		try {
			setDrive(await api.get<Drive>(`/drives/${driveId}`))
		} catch (err) {
			setError(err instanceof ApiError ? err.message : "Could not load drive.")
		}
	}, [driveId])

	const loadEligibility = useCallback(async () => {
		setLoading(true)
		setError(null)
		try {
			const rows = await api.get<Eligibility[]>(
				`/drives/${driveId}/eligibility?eligible_only=${eligibleOnly}`,
			)
			setEligibility(rows)
		} catch (err) {
			setError(
				err instanceof ApiError ? err.message : "Could not run eligibility.",
			)
		} finally {
			setLoading(false)
		}
	}, [driveId, eligibleOnly])

	const loadApplicants = useCallback(async () => {
		setLoading(true)
		setError(null)
		try {
			setApplicants(
				await api.get<Applicant[]>(`/drives/${driveId}/applications`),
			)
		} catch (err) {
			setError(
				err instanceof ApiError ? err.message : "Could not load applicants.",
			)
		} finally {
			setLoading(false)
		}
	}, [driveId])

	useEffect(() => {
		loadDrive()
	}, [loadDrive])

	useEffect(() => {
		if (tab === "eligibility") loadEligibility()
		else loadApplicants()
	}, [tab, loadEligibility, loadApplicants])

	async function decide(applicant: Applicant, status: AppStatus) {
		setError(null)
		try {
			await api.patch(
				`/drives/applications/${applicant.application_id}/status`,
				{ status },
			)
			await loadApplicants()
		} catch (err) {
			setError(
				err instanceof ApiError ? err.message : "Could not update applicant.",
			)
		}
	}

	const tabClass = (active: boolean) =>
		`rounded-lg px-4 py-2 text-sm transition ${
			active ? "bg-indigo-50 dark:bg-indigo-500/15 text-indigo-700 dark:text-indigo-200" : "text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-white/10"
		}`

	return (
		<div>
			<Link
				href="/dashboard/drives"
				className="text-sm text-slate-500 dark:text-slate-400 transition hover:text-slate-900 dark:hover:text-white"
			>
				← Back to drives
			</Link>

			{/* Drive header */}
			<div className="mt-3 flex flex-wrap items-center gap-3">
				<h2 className="text-2xl font-bold">
					{drive ? drive.company_name : "Drive"}
				</h2>
				{drive && (
					<span
						className={`rounded-full px-2 py-0.5 text-xs ${
							drive.is_open
								? "bg-emerald-500/15 text-emerald-600 dark:text-emerald-300"
								: "bg-slate-500/15 text-slate-500 dark:text-slate-400"
						}`}
					>
						{drive.is_open ? "Open" : "Closed"}
					</span>
				)}
			</div>
			{drive && (
				<p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
					{drive.role_title}
					{drive.package_lpa != null ? ` · ${drive.package_lpa} LPA` : ""} · Min
					CGPA {drive.min_cgpa} · Min attendance {drive.min_attendance}% · Min
					projects {drive.min_verified_projects}
					{drive.required_skills ? ` · Skills: ${drive.required_skills}` : ""}
				</p>
			)}

			{/* Tabs */}
			<div className="mt-6 flex gap-2">
				<button
					onClick={() => setTab("eligibility")}
					className={tabClass(tab === "eligibility")}
				>
					Eligibility
				</button>
				<button
					onClick={() => setTab("applicants")}
					className={tabClass(tab === "applicants")}
				>
					Applicants
				</button>
			</div>

			{error && (
				<p className="mt-4 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">
					{error}
				</p>
			)}

			{/* Eligibility tab */}
			{tab === "eligibility" && (
				<div className="mt-5">
					<label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
						<input
							type="checkbox"
							checked={eligibleOnly}
							onChange={(e) => setEligibleOnly(e.target.checked)}
						/>
						Show eligible students only
					</label>

					{loading ? (
						<p className="mt-4 text-slate-500 dark:text-slate-400">Running eligibility engine...</p>
					) : eligibility.length === 0 ? (
						<p className="mt-4 text-slate-500 dark:text-slate-400">No students to evaluate.</p>
					) : (
						<div className="mt-4 space-y-3">
							{eligibility.map((row) => (
								<div
									key={row.student_id}
								className="rounded-xl border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-900 p-4"
								>
									<div className="flex flex-wrap items-center justify-between gap-2">
										<div className="font-medium">{row.full_name}</div>
										<span
											className={`rounded-full px-2 py-0.5 text-xs ${
												row.eligible
													? "bg-emerald-500/15 text-emerald-600 dark:text-emerald-300"
													: "bg-red-500/15 text-red-300"
											}`}
										>
											{row.eligible ? "Eligible" : "Not eligible"}
										</span>
									</div>
									<div className="mt-1 text-xs text-slate-500 dark:text-slate-400">
										CGPA {row.cgpa} · Attendance {row.attendance}% · Verified
										skills {row.verified_skills} · Verified projects{" "}
										{row.verified_projects}
									</div>
									<div className="mt-3 flex flex-wrap gap-2">
										{row.reasons.map((reason) => (
											<span
												key={reason.criterion}
												className={`rounded-md px-2 py-1 text-xs ${
													reason.passed
														? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-300"
														: "bg-red-500/10 text-red-300"
												}`}
											>
												{reason.passed ? "✓" : "✗"} {reason.criterion}:{" "}
												{reason.detail}
											</span>
										))}
									</div>
								</div>
							))}
						</div>
					)}
				</div>
			)}

			{/* Applicants tab */}
			{tab === "applicants" && (
				<div className="mt-5">
					{loading ? (
						<p className="text-slate-500 dark:text-slate-400">Loading applicants...</p>
					) : applicants.length === 0 ? (
						<p className="text-slate-500 dark:text-slate-400">No applications yet.</p>
					) : (
						<div className="space-y-3">
							{applicants.map((applicant) => (
								<div
									key={applicant.application_id}
									className="rounded-xl border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-900 p-4"
								>
									<div className="flex flex-wrap items-center justify-between gap-2">
										<div className="font-medium">{applicant.full_name}</div>
										<span
											className={`rounded-full px-2 py-0.5 text-xs capitalize ${STATUS_STYLES[applicant.status]}`}
										>
											{applicant.status}
										</span>
									</div>
									<div className="mt-1 text-xs text-slate-500 dark:text-slate-400">
										CGPA {applicant.cgpa} · Attendance {applicant.attendance}% ·
										Verified skills {applicant.verified_skills} · Verified
										projects {applicant.verified_projects}
										{applicant.eligible ? "" : " · (no longer eligible)"}
									</div>
									<div className="mt-3 flex gap-2">
										<button
											onClick={() => decide(applicant, "shortlisted")}
											disabled={applicant.status === "shortlisted"}
											className="rounded-lg border border-amber-400/30 px-3 py-1.5 text-sm text-amber-600 dark:text-amber-300 transition hover:bg-amber-400/10 disabled:opacity-40"
										>
											Shortlist
										</button>
										<button
											onClick={() => decide(applicant, "selected")}
											disabled={applicant.status === "selected"}
											className="rounded-lg border border-emerald-400/30 px-3 py-1.5 text-sm text-emerald-600 dark:text-emerald-300 transition hover:bg-emerald-400/10 disabled:opacity-40"
										>
											Select
										</button>
										<button
											onClick={() => decide(applicant, "rejected")}
											disabled={applicant.status === "rejected"}
											className="rounded-lg border border-red-400/30 px-3 py-1.5 text-sm text-red-300 transition hover:bg-red-400/10 disabled:opacity-40"
										>
											Reject
										</button>
									</div>
								</div>
							))}
						</div>
					)}
				</div>
			)}
		</div>
	)
}
