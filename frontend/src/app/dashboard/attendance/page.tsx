/**
 * Campus AI - Attendance page (role-aware).
 *
 * Place this file at: src/app/dashboard/attendance/page.tsx
 *
 * One route, two views (teacher and student share /dashboard/attendance):
 *   - Students see their own attendance summary + recent records.
 *   - Teachers/admins get a marking tool: pick department -> section -> date,
 *     load the section roster, mark each student present/absent/late, submit.
 *
 * Backend endpoints:
 *   Student view:
 *     GET  /attendance/me/summary -> { total, present, absent, late, percentage }
 *     GET  /attendance/me         -> [{ id, student_id, section_id, date, status }]
 *   Teacher view:
 *     GET  /admin/departments                 -> [{ id, name, code }]
 *     GET  /admin/departments/{id}/sections    -> [{ id, name, year, department_id }]
 *     GET  /people/students?section_id={id}    -> [{ id, full_name, email, role, ... }]
 *     POST /attendance/mark  body { section_id, date, records: [{ student_id, status }] }
 */

"use client"

import { useCallback, useEffect, useState } from "react"
import { api, ApiError } from "@/lib/api"
import { useCurrentUser } from "@/lib/auth"

type AttendanceStatus = "present" | "absent" | "late"

const STATUS_STYLES: Record<AttendanceStatus, string> = {
	present: "bg-emerald-500/15 text-emerald-300",
	late: "bg-amber-500/15 text-amber-300",
	absent: "bg-red-500/15 text-red-300",
}

const STATUS_ORDER: AttendanceStatus[] = ["present", "late", "absent"]

function percentColor(pct: number): string {
	if (pct >= 75) return "text-emerald-400"
	if (pct >= 60) return "text-amber-400"
	return "text-red-400"
}

/** Top-level page: route to the right view based on the signed-in role. */
export default function AttendancePage() {
	const { user, loading } = useCurrentUser()

	if (loading || !user) {
		return <p className="text-slate-400">Loading...</p>
	}

	if (user.role === "teacher" || user.role === "admin") {
		return <TeacherAttendance />
	}
	return <StudentAttendance />
}

/* ----------------------------- Teacher view ----------------------------- */

type Department = { id: number; name: string; code: string }
type Section = {
	id: number
	name: string
	year: number | null
	department_id: number
}
type Student = { id: number; full_name: string; email: string }

function todayIso(): string {
	return new Date().toISOString().slice(0, 10)
}

function TeacherAttendance() {
	const [departments, setDepartments] = useState<Department[]>([])
	const [sections, setSections] = useState<Section[]>([])
	const [roster, setRoster] = useState<Student[]>([])
	const [statuses, setStatuses] = useState<Record<number, AttendanceStatus>>({})

	const [deptId, setDeptId] = useState<number | null>(null)
	const [sectionId, setSectionId] = useState<number | null>(null)
	const [date, setDate] = useState<string>(todayIso())

	const [loadingRoster, setLoadingRoster] = useState(false)
	const [saving, setSaving] = useState(false)
	const [error, setError] = useState<string | null>(null)
	const [success, setSuccess] = useState<string | null>(null)

	// Load departments once.
	useEffect(() => {
		api
			.get<Department[]>("/admin/departments")
			.then(setDepartments)
			.catch((err) =>
				setError(
					err instanceof ApiError
						? err.message
						: "Could not load departments.",
				),
			)
	}, [])

	// When the department changes, load its sections and reset downstream state.
	useEffect(() => {
		setSections([])
		setSectionId(null)
		setRoster([])
		setStatuses({})
		setSuccess(null)
		if (deptId == null) return
		api
			.get<Section[]>(`/admin/departments/${deptId}/sections`)
			.then(setSections)
			.catch((err) =>
				setError(
					err instanceof ApiError ? err.message : "Could not load sections.",
				),
			)
	}, [deptId])

	const loadRoster = useCallback(async () => {
		if (sectionId == null) return
		setLoadingRoster(true)
		setError(null)
		setSuccess(null)
		try {
			const students = await api.get<Student[]>(
				`/people/students?section_id=${sectionId}`,
			)
			setRoster(students)
			const initial: Record<number, AttendanceStatus> = {}
			for (const s of students) initial[s.id] = "present"
			setStatuses(initial)
		} catch (err) {
			setError(
				err instanceof ApiError ? err.message : "Could not load the roster.",
			)
		} finally {
			setLoadingRoster(false)
		}
	}, [sectionId])

	// Auto-load the roster whenever a section is chosen.
	useEffect(() => {
		if (sectionId != null) loadRoster()
	}, [sectionId, loadRoster])

	function setStatus(studentId: number, status: AttendanceStatus) {
		setStatuses((prev) => ({ ...prev, [studentId]: status }))
	}

	function markAll(status: AttendanceStatus) {
		const next: Record<number, AttendanceStatus> = {}
		for (const s of roster) next[s.id] = status
		setStatuses(next)
	}

	async function submit() {
		if (sectionId == null || roster.length === 0) return
		setSaving(true)
		setError(null)
		setSuccess(null)
		try {
			const payload = {
				section_id: sectionId,
				date,
				records: roster.map((s) => ({
					student_id: s.id,
					status: statuses[s.id] ?? "present",
				})),
			}
			await api.post("/attendance/mark", payload)
			setSuccess(
				`Attendance saved for ${roster.length} students on ${date}.`,
			)
		} catch (err) {
			setError(
				err instanceof ApiError ? err.message : "Could not save attendance.",
			)
		} finally {
			setSaving(false)
		}
	}

	const selectClass =
		"mt-1 w-full rounded-lg border border-white/10 bg-slate-900 px-3 py-2 text-sm outline-none focus:border-indigo-400"

	const counts = STATUS_ORDER.reduce<Record<AttendanceStatus, number>>(
		(acc, st) => {
			acc[st] = roster.filter(
				(s) => (statuses[s.id] ?? "present") === st,
			).length
			return acc
		},
		{ present: 0, late: 0, absent: 0 },
	)

	return (
		<div>
			<h2 className="text-2xl font-bold">Take Attendance</h2>
			<p className="mt-1 text-sm text-slate-400">
				Pick a section and date, then mark each student. Saving again for the
				same date updates those records.
			</p>

			{/* Selectors */}
			<div className="mt-6 grid gap-4 sm:grid-cols-3">
				<div>
					<label className="text-sm text-slate-400">Department</label>
					<select
						value={deptId ?? ""}
						onChange={(e) =>
							setDeptId(e.target.value ? Number(e.target.value) : null)
						}
						className={selectClass}
					>
						<option value="">Select department</option>
						{departments.map((d) => (
							<option key={d.id} value={d.id}>
								{d.name} ({d.code})
							</option>
						))}
					</select>
				</div>
				<div>
					<label className="text-sm text-slate-400">Section</label>
					<select
						value={sectionId ?? ""}
						onChange={(e) =>
							setSectionId(e.target.value ? Number(e.target.value) : null)
						}
						disabled={deptId == null}
						className={selectClass}
					>
						<option value="">Select section</option>
						{sections.map((s) => (
							<option key={s.id} value={s.id}>
								{s.name}
								{s.year ? ` - Year ${s.year}` : ""}
							</option>
						))}
					</select>
				</div>
				<div>
					<label className="text-sm text-slate-400">Date</label>
					<input
						type="date"
						value={date}
						onChange={(e) => setDate(e.target.value)}
						className={selectClass}
					/>
				</div>
			</div>

			{error && (
				<p className="mt-4 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">
					{error}
				</p>
			)}
			{success && (
				<p className="mt-4 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-300">
					{success}
				</p>
			)}

			{/* Roster */}
			{loadingRoster ? (
				<p className="mt-6 text-slate-400">Loading roster...</p>
			) : sectionId == null ? (
				<p className="mt-6 text-slate-400">
					Select a section to load its students.
				</p>
			) : roster.length === 0 ? (
				<p className="mt-6 text-slate-400">
					No students assigned to this section yet. An admin can assign students
					to a section from the Users area.
				</p>
			) : (
				<>
					{/* Bulk actions + live counts */}
					<div className="mt-6 flex flex-wrap items-center justify-between gap-3">
						<div className="text-sm text-slate-400">
							<span className="text-emerald-300">
								{counts.present} present
							</span>
							{" / "}
							<span className="text-amber-300">{counts.late} late</span>
							{" / "}
							<span className="text-red-300">{counts.absent} absent</span>
						</div>
						<div className="flex gap-2">
							{STATUS_ORDER.map((st) => (
								<button
									key={st}
									onClick={() => markAll(st)}
									className="rounded-lg border border-white/10 px-3 py-1.5 text-xs capitalize text-slate-300 transition hover:bg-white/5"
								>
									All {st}
								</button>
							))}
						</div>
					</div>

					<div className="mt-3 space-y-2">
						{roster.map((s) => (
							<div
								key={s.id}
								className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-white/10 bg-white/5 px-4 py-3"
							>
								<div>
									<p className="font-medium">{s.full_name}</p>
									<p className="text-xs text-slate-500">{s.email}</p>
								</div>
								<div className="flex gap-2">
									{STATUS_ORDER.map((st) => {
										const active = (statuses[s.id] ?? "present") === st
										return (
											<button
												key={st}
												onClick={() => setStatus(s.id, st)}
												className={`rounded-lg px-3 py-1.5 text-xs capitalize transition ${
													active
														? STATUS_STYLES[st]
														: "text-slate-400 hover:bg-white/5"
												}`}
											>
												{st}
											</button>
										)
									})}
								</div>
							</div>
						))}
					</div>

					<div className="mt-6">
						<button
							onClick={submit}
							disabled={saving}
							className="rounded-lg bg-gradient-to-r from-indigo-500 to-violet-500 px-5 py-2.5 text-sm font-medium text-white transition hover:opacity-90 disabled:opacity-40"
						>
							{saving ? "Saving..." : "Save attendance"}
						</button>
					</div>
				</>
			)}
		</div>
	)
}

/* ----------------------------- Student view ----------------------------- */

type Summary = {
	total: number
	present: number
	absent: number
	late: number
	percentage: number
}

type AttendanceRecord = {
	id: number
	student_id: number
	section_id: number
	date: string
	status: AttendanceStatus
}

function StudentAttendance() {
	const [summary, setSummary] = useState<Summary | null>(null)
	const [records, setRecords] = useState<AttendanceRecord[]>([])
	const [loading, setLoading] = useState(true)
	const [error, setError] = useState<string | null>(null)

	useEffect(() => {
		async function load() {
			setLoading(true)
			setError(null)
			try {
				const [s, r] = await Promise.all([
					api.get<Summary>("/attendance/me/summary"),
					api.get<AttendanceRecord[]>("/attendance/me"),
				])
				setSummary(s)
				setRecords(r)
			} catch (err) {
				setError(
					err instanceof ApiError
						? err.message
						: "Could not load attendance.",
				)
			} finally {
				setLoading(false)
			}
		}
		load()
	}, [])

	return (
		<div>
			<h2 className="text-2xl font-bold">My Attendance</h2>
			<p className="mt-1 text-sm text-slate-400">
				Your overall attendance. 'Late' is counted as attended.
			</p>

			{error && (
				<p className="mt-4 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">
					{error}
				</p>
			)}

			{loading ? (
				<p className="mt-6 text-slate-400">Loading your attendance...</p>
			) : summary && summary.total === 0 ? (
				<p className="mt-6 text-slate-400">No attendance records yet.</p>
			) : (
				summary && (
					<>
						{/* Summary */}
						<div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
							<div className="rounded-2xl border border-white/10 bg-white/5 p-6">
								<p className="text-sm text-slate-400">Overall</p>
								<p
									className={`mt-1 text-4xl font-bold ${percentColor(
										summary.percentage,
									)}`}
								>
									{summary.percentage}%
								</p>
								<p className="mt-1 text-xs text-slate-500">
									{summary.present + summary.late}/{summary.total} classes
								</p>
							</div>
							<div className="rounded-2xl border border-white/10 bg-white/5 p-6">
								<p className="text-sm text-slate-400">Present</p>
								<p className="mt-1 text-4xl font-bold text-emerald-400">
									{summary.present}
								</p>
							</div>
							<div className="rounded-2xl border border-white/10 bg-white/5 p-6">
								<p className="text-sm text-slate-400">Late</p>
								<p className="mt-1 text-4xl font-bold text-amber-400">
									{summary.late}
								</p>
							</div>
							<div className="rounded-2xl border border-white/10 bg-white/5 p-6">
								<p className="text-sm text-slate-400">Absent</p>
								<p className="mt-1 text-4xl font-bold text-red-400">
									{summary.absent}
								</p>
							</div>
						</div>

						{/* Records */}
						<div className="mt-8">
							<h3 className="text-lg font-semibold">Recent records</h3>
							<div className="mt-3 space-y-2">
								{records.map((record) => (
									<div
										key={record.id}
										className="flex items-center justify-between rounded-xl border border-white/10 bg-white/5 px-4 py-3"
									>
										<span className="text-sm text-slate-300">
											{record.date}
										</span>
										<span
											className={`rounded-full px-2 py-0.5 text-xs capitalize ${STATUS_STYLES[record.status]}`}
										>
											{record.status}
										</span>
									</div>
								))}
							</div>
						</div>
					</>
				)
			)}
		</div>
	)
}
