/**
 * Campus AI - Student Placements page (browse drives + apply).
 *
 * Place this file at: src/app/dashboard/placements/page.tsx
 *
 * The student browses currently OPEN drives, checks their own eligibility
 * (computed from their VERIFIED data, with per-criterion reasons), applies to
 * eligible drives, and tracks their applications. This closes the placement
 * loop: an application here shows up for the TPO on the drive's applicants.
 *
 * Backend endpoints:
 *   GET  /drives/open
 *   GET  /drives/{id}/my-eligibility
 *   POST /drives/{id}/apply
 *   GET  /drives/me/applications
 */

"use client"

import { useEffect, useState } from "react"
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

type MyEligibility = {
	drive_id: number
	eligible: boolean
	cgpa: number
	attendance: number
	verified_skills: number
	verified_projects: number
	reasons: Reason[]
}

type AppStatus = "applied" | "shortlisted" | "selected" | "rejected"

type MyApplication = {
	id: number
	status: AppStatus
	note: string | null
	drive: {
		id: number
		company_name: string
		role_title: string
		package_lpa: number | null
		is_open: boolean
	}
}

const STATUS_STYLES: Record<AppStatus, string> = {
	applied: "bg-slate-500/15 text-slate-600 dark:text-slate-300",
	shortlisted: "bg-amber-500/15 text-amber-600 dark:text-amber-300",
	selected: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-300",
	rejected: "bg-red-500/15 text-red-300",
}

export default function PlacementsPage() {
	const [tab, setTab] = useState<"open" | "mine">("open")
	const [openDrives, setOpenDrives] = useState<Drive[]>([])
	const [myApps, setMyApps] = useState<MyApplication[]>([])
	const [elig, setElig] = useState<Record<number, MyEligibility>>({})
	const [loading, setLoading] = useState(true)
	const [busyId, setBusyId] = useState<number | null>(null)
	const [error, setError] = useState<string | null>(null)
	const [notice, setNotice] = useState<string | null>(null)

	async function loadAll() {
		setLoading(true)
		setError(null)
		try {
			const [drives, apps] = await Promise.all([
				api.get<Drive[]>("/drives/open"),
				api.get<MyApplication[]>("/drives/me/applications"),
			])
			setOpenDrives(drives)
			setMyApps(apps)
		} catch (err) {
			setError(
				err instanceof ApiError ? err.message : "Could not load placements.",
			)
		} finally {
			setLoading(false)
		}
	}

	useEffect(() => {
		loadAll()
	}, [])

	async function checkEligibility(driveId: number) {
		setError(null)
		setNotice(null)
		setBusyId(driveId)
		try {
			const result = await api.get<MyEligibility>(
				`/drives/${driveId}/my-eligibility`,
			)
			setElig((prev) => ({ ...prev, [driveId]: result }))
		} catch (err) {
			setError(
				err instanceof ApiError ? err.message : "Could not check eligibility.",
			)
		} finally {
			setBusyId(null)
		}
	}

	async function apply(driveId: number) {
		setError(null)
		setNotice(null)
		setBusyId(driveId)
		try {
			await api.post(`/drives/${driveId}/apply`, {})
			setNotice("Application submitted.")
			await loadAll()
		} catch (err) {
			setError(
				err instanceof ApiError ? err.message : "Could not apply to this drive.",
			)
		} finally {
			setBusyId(null)
		}
	}

	const appliedDriveIds = new Set(myApps.map((a) => a.drive.id))

	const tabClass = (active: boolean) =>
		`rounded-lg px-4 py-2 text-sm transition ${
			active ? "bg-indigo-50 dark:bg-indigo-500/15 text-indigo-700 dark:text-indigo-200" : "text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-white/10"
		}`

	return (
		<div>
			<h2 className="text-2xl font-bold">Placements</h2>
			<p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
				Browse open drives, check your eligibility on verified data, and apply.
			</p>

			<div className="mt-6 flex gap-2">
				<button onClick={() => setTab("open")} className={tabClass(tab === "open")}>
					Open drives
				</button>
				<button onClick={() => setTab("mine")} className={tabClass(tab === "mine")}>
					My applications
				</button>
			</div>

			{error && (
				<p className="mt-4 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">
					{error}
				</p>
			)}
			{notice && (
				<p className="mt-4 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-600 dark:text-emerald-300">
					{notice}
				</p>
			)}

			{/* Open drives tab */}
			{tab === "open" && (
				<div className="mt-6">
					{loading ? (
						<p className="text-slate-500 dark:text-slate-400">Loading drives...</p>
					) : openDrives.length === 0 ? (
						<p className="text-slate-500 dark:text-slate-400">No open drives right now.</p>
					) : (
						<div className="space-y-4">
							{openDrives.map((drive) => {
								const result = elig[drive.id]
								const already = appliedDriveIds.has(drive.id)
								return (
									<div
										key={drive.id}
										className="rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-900 p-5"
									>
										<div className="flex flex-wrap items-start justify-between gap-3">
											<div>
												<h3 className="text-lg font-semibold">
													{drive.company_name}
												</h3>
												<p className="text-sm text-slate-600 dark:text-slate-300">
													{drive.role_title}
													{drive.location ? ` · ${drive.location}` : ""}
													{drive.package_lpa != null
														? ` · ${drive.package_lpa} LPA`
														: ""}
												</p>
											</div>
											<div className="flex gap-2">
												<button
													onClick={() => checkEligibility(drive.id)}
													disabled={busyId === drive.id}
													className="rounded-lg border border-slate-300 dark:border-white/15 px-3 py-1.5 text-sm transition hover:bg-slate-100 dark:hover:bg-white/10 disabled:opacity-50"
												>
													Check eligibility
												</button>
												<button
													onClick={() => apply(drive.id)}
													disabled={busyId === drive.id || already}
													className="rounded-lg bg-gradient-to-r from-indigo-500 to-violet-500 px-4 py-1.5 text-sm font-medium text-white transition hover:opacity-90 disabled:opacity-50"
												>
													{already ? "Applied" : "Apply"}
												</button>
											</div>
										</div>

										<div className="mt-4 flex flex-wrap gap-2 text-xs text-slate-600 dark:text-slate-300">
											<span className="rounded-md bg-white dark:bg-slate-900 px-2 py-1">
												Min CGPA: {drive.min_cgpa}
											</span>
											<span className="rounded-md bg-white dark:bg-slate-900 px-2 py-1">
												Min attendance: {drive.min_attendance}%
											</span>
											<span className="rounded-md bg-white dark:bg-slate-900 px-2 py-1">
												Min projects: {drive.min_verified_projects}
											</span>
											{drive.required_skills && (
												<span className="rounded-md bg-white dark:bg-slate-900 px-2 py-1">
													Skills: {drive.required_skills}
												</span>
											)}
											{drive.deadline && (
												<span className="rounded-md bg-white dark:bg-slate-900 px-2 py-1">
													Deadline: {drive.deadline}
												</span>
											)}
										</div>

										{/* Eligibility result (after Check) */}
										{result && (
											<div className="mt-4 rounded-xl border border-slate-200 dark:border-white/10 bg-white/40 p-3">
												<div className="flex items-center gap-2">
													<span
														className={`rounded-full px-2 py-0.5 text-xs ${
														result.eligible
															? "bg-emerald-500/15 text-emerald-600 dark:text-emerald-300"
															: "bg-red-500/15 text-red-300"
													}`}
													>
														{result.eligible ? "You are eligible" : "Not eligible"}
													</span>
													<span className="text-xs text-slate-500 dark:text-slate-400">
														CGPA {result.cgpa} · Attendance {result.attendance}% ·
														Skills {result.verified_skills} · Projects{" "}
														{result.verified_projects}
													</span>
												</div>
												<div className="mt-2 flex flex-wrap gap-2">
													{result.reasons.map((reason) => (
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
										)}
									</div>
								)
							})}
						</div>
					)}
				</div>
			)}

			{/* My applications tab */}
			{tab === "mine" && (
				<div className="mt-6">
					{loading ? (
						<p className="text-slate-500 dark:text-slate-400">Loading...</p>
					) : myApps.length === 0 ? (
						<p className="text-slate-500 dark:text-slate-400">
							You have not applied to any drive yet.
						</p>
					) : (
						<div className="space-y-3">
							{myApps.map((application) => (
								<div
									key={application.id}
									className="rounded-xl border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-900 p-4"
								>
									<div className="flex flex-wrap items-center justify-between gap-2">
										<div>
											<div className="font-medium">
												{application.drive.company_name}
											</div>
											<div className="text-xs text-slate-500 dark:text-slate-400">
												{application.drive.role_title}
												{application.drive.package_lpa != null
													? ` · ${application.drive.package_lpa} LPA`
													: ""}
											</div>
										</div>
										<span
											className={`rounded-full px-2 py-0.5 text-xs capitalize ${STATUS_STYLES[application.status]}`}
										>
											{application.status}
										</span>
									</div>
									{application.note && (
										<p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
											TPO note: {application.note}
										</p>
									)}
								</div>
							))}
						</div>
					)}
				</div>
			)}
		</div>
	)
}
