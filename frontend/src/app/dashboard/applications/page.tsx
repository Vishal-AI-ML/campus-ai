/**
 * Campus AI - TPO applications inbox (cross-drive).
 *
 * Place this file at: src/app/dashboard/applications/page.tsx
 *
 * Pick a drive, see its applicants (with a verified-data snapshot), filter by
 * status, and shortlist / select / reject. This is the dedicated workspace
 * version of the applicants tab on a single drive.
 *
 * Backend endpoints:
 *   GET   /drives                                     (drive list)
 *   GET   /drives/{id}/applications?status_filter=    (applicants)
 *   PATCH /drives/applications/{application_id}/status  body: { status, note? }
 */

"use client"

import { useCallback, useEffect, useState } from "react"
import Link from "next/link"
import { api, ApiError } from "@/lib/api"

type Drive = {
	id: number
	company_name: string
	role_title: string
	is_open: boolean
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
	applied: "bg-slate-500/15 text-slate-300",
	shortlisted: "bg-amber-500/15 text-amber-300",
	selected: "bg-emerald-500/15 text-emerald-300",
	rejected: "bg-red-500/15 text-red-300",
}

export default function ApplicationsPage() {
	const [drives, setDrives] = useState<Drive[]>([])
	const [selectedDriveId, setSelectedDriveId] = useState<number | null>(null)
	const [statusFilter, setStatusFilter] = useState<"" | AppStatus>("")
	const [applicants, setApplicants] = useState<Applicant[]>([])
	const [loading, setLoading] = useState(true)
	const [loadingApps, setLoadingApps] = useState(false)
	const [error, setError] = useState<string | null>(null)

	// Load the drive list once; default-select the first drive.
	useEffect(() => {
		;(async () => {
			setLoading(true)
			setError(null)
			try {
				const rows = await api.get<Drive[]>("/drives")
				setDrives(rows)
				if (rows.length > 0) setSelectedDriveId(rows[0].id)
			} catch (err) {
				setError(
					err instanceof ApiError ? err.message : "Could not load drives.",
				)
			} finally {
				setLoading(false)
			}
		})()
	}, [])

	const loadApplicants = useCallback(async () => {
		if (selectedDriveId == null) {
			setApplicants([])
			return
		}
		setLoadingApps(true)
		setError(null)
		try {
			const qs = statusFilter ? `?status_filter=${statusFilter}` : ""
			setApplicants(
				await api.get<Applicant[]>(
					`/drives/${selectedDriveId}/applications${qs}`,
				),
			)
		} catch (err) {
			setError(
				err instanceof ApiError ? err.message : "Could not load applicants.",
			)
		} finally {
			setLoadingApps(false)
		}
	}, [selectedDriveId, statusFilter])

	useEffect(() => {
		loadApplicants()
	}, [loadApplicants])

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

	const selectClass =
		"rounded-lg border border-white/10 bg-slate-900 px-3 py-2 text-sm outline-none focus:border-indigo-400"

	return (
		<div>
			<h2 className="text-2xl font-bold">Applications</h2>
			<p className="mt-1 text-sm text-slate-400">
				Review applicants per drive and decide who moves forward.
			</p>

			{error && (
				<p className="mt-4 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">
					{error}
				</p>
			)}

			{loading ? (
				<p className="mt-6 text-slate-400">Loading drives...</p>
			) : drives.length === 0 ? (
				<p className="mt-6 text-slate-400">
					No drives yet. Create one on the{" "}
					<Link href="/dashboard/drives" className="text-indigo-300 underline">
						Drives
					</Link>{" "}
					page first.
				</p>
			) : (
				<>
					{/* Controls */}
					<div className="mt-6 flex flex-wrap items-center gap-3">
						<select
							value={selectedDriveId ?? ""}
							onChange={(e) => setSelectedDriveId(Number(e.target.value))}
							className={selectClass}
						>
							{drives.map((drive) => (
								<option key={drive.id} value={drive.id}>
									{drive.company_name} — {drive.role_title}
									{drive.is_open ? "" : " (closed)"}
								</option>
							))}
						</select>

						<select
							value={statusFilter}
							onChange={(e) =>
								setStatusFilter(e.target.value as "" | AppStatus)
							}
							className={selectClass}
						>
							<option value="">All statuses</option>
							<option value="applied">Applied</option>
							<option value="shortlisted">Shortlisted</option>
							<option value="selected">Selected</option>
							<option value="rejected">Rejected</option>
						</select>

						{selectedDriveId != null && (
							<Link
								href={`/dashboard/drives/${selectedDriveId}`}
								className="text-sm text-slate-400 transition hover:text-white"
							>
								Open drive detail →
							</Link>
						)}
					</div>

					{/* Applicants */}
					<div className="mt-6">
						{loadingApps ? (
							<p className="text-slate-400">Loading applicants...</p>
						) : applicants.length === 0 ? (
							<p className="text-slate-400">
								No applications for this drive yet.
							</p>
						) : (
							<div className="space-y-3">
								{applicants.map((applicant) => (
									<div
										key={applicant.application_id}
										className="rounded-xl border border-white/10 bg-white/5 p-4"
									>
										<div className="flex flex-wrap items-center justify-between gap-2">
											<div className="font-medium">{applicant.full_name}</div>
											<span
												className={`rounded-full px-2 py-0.5 text-xs capitalize ${STATUS_STYLES[applicant.status]}`}
											>
												{applicant.status}
											</span>
										</div>
										<div className="mt-1 text-xs text-slate-400">
											CGPA {applicant.cgpa} · Attendance {applicant.attendance}% ·
											Verified skills {applicant.verified_skills} · Verified
											projects {applicant.verified_projects}
											{applicant.eligible ? "" : " · (no longer eligible)"}
										</div>
										<div className="mt-3 flex gap-2">
											<button
												onClick={() => decide(applicant, "shortlisted")}
												disabled={applicant.status === "shortlisted"}
												className="rounded-lg border border-amber-400/30 px-3 py-1.5 text-sm text-amber-300 transition hover:bg-amber-400/10 disabled:opacity-40"
											>
												Shortlist
											</button>
											<button
												onClick={() => decide(applicant, "selected")}
												disabled={applicant.status === "selected"}
												className="rounded-lg border border-emerald-400/30 px-3 py-1.5 text-sm text-emerald-300 transition hover:bg-emerald-400/10 disabled:opacity-40"
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
				</>
			)}
		</div>
	)
}
