/**
 * Campus AI - Admin: Departments & Sections structure.
 *
 * Place this file at: src/app/dashboard/departments/page.tsx
 *
 * The institute backbone. Admin creates departments, and within each
 * department creates sections (classes). Everything downstream - subjects,
 * student rosters, attendance, gradebook - hangs off this structure, so it is
 * the first admin screen.
 *
 * Backend endpoints:
 *   GET  /admin/departments                       -> [{ id, name, code }]
 *   POST /admin/departments                        body { name, code }
 *   GET  /admin/departments/{id}/sections          -> [{ id, name, year, department_id }]
 *   POST /admin/departments/{id}/sections          body { name, year? }
 */

"use client"

import { useCallback, useEffect, useState } from "react"
import { api, ApiError } from "@/lib/api"

type Department = { id: number; name: string; code: string }
type Section = {
	id: number
	name: string
	year: number | null
	department_id: number
}

const inputClass =
	"mt-1 w-full rounded-lg border border-white/10 bg-slate-900 px-3 py-2 text-sm outline-none focus:border-indigo-400"

const primaryBtn =
	"mt-3 rounded-lg bg-gradient-to-r from-indigo-500 to-violet-500 px-4 py-2 text-sm font-medium text-white transition hover:opacity-90 disabled:opacity-40"

export default function DepartmentsPage() {
	const [departments, setDepartments] = useState<Department[]>([])
	const [selectedId, setSelectedId] = useState<number | null>(null)
	const [loadingDepts, setLoadingDepts] = useState(true)
	const [deptError, setDeptError] = useState<string | null>(null)

	const [newName, setNewName] = useState("")
	const [newCode, setNewCode] = useState("")
	const [creatingDept, setCreatingDept] = useState(false)
	const [createDeptError, setCreateDeptError] = useState<string | null>(null)

	const loadDepartments = useCallback(async () => {
		setLoadingDepts(true)
		setDeptError(null)
		try {
			setDepartments(await api.get<Department[]>("/admin/departments"))
		} catch (err) {
			setDeptError(
				err instanceof ApiError
					? err.message
					: "Could not load departments.",
			)
		} finally {
			setLoadingDepts(false)
		}
	}, [])

	useEffect(() => {
		loadDepartments()
	}, [loadDepartments])

	async function createDepartment() {
		if (!newName.trim() || !newCode.trim()) {
			setCreateDeptError("Name and code are required.")
			return
		}
		setCreatingDept(true)
		setCreateDeptError(null)
		try {
			const payload = { name: newName.trim(), code: newCode.trim() }
			await api.post("/admin/departments", payload)
			setNewName("")
			setNewCode("")
			await loadDepartments()
		} catch (err) {
			setCreateDeptError(
				err instanceof ApiError
					? err.message
					: "Could not create department.",
			)
		} finally {
			setCreatingDept(false)
		}
	}

	const selected = departments.find((d) => d.id === selectedId) ?? null

	return (
		<div>
			<h2 className="text-2xl font-bold">Departments & Sections</h2>
			<p className="mt-1 text-sm text-slate-400">
				The institute structure. Create departments, then add sections inside
				each one. Subjects, rosters and attendance all build on this.
			</p>

			<div className="mt-6 grid gap-6 lg:grid-cols-2">
				{/* Departments column */}
				<div>
					<div className="rounded-2xl border border-white/10 bg-white/5 p-6">
						<h3 className="text-lg font-semibold">Add a department</h3>
						<div className="mt-3 grid gap-3 sm:grid-cols-2">
							<div>
								<label className="text-sm text-slate-400">Name</label>
								<input
									value={newName}
									onChange={(e) => setNewName(e.target.value)}
									className={inputClass}
									placeholder="Computer Science"
								/>
							</div>
							<div>
								<label className="text-sm text-slate-400">Code</label>
								<input
									value={newCode}
									onChange={(e) => setNewCode(e.target.value)}
									className={inputClass}
									placeholder="CSE"
								/>
							</div>
						</div>
						{createDeptError && (
							<p className="mt-3 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">
								{createDeptError}
							</p>
						)}
						<button
							onClick={createDepartment}
							disabled={creatingDept}
							className={primaryBtn}
						>
							{creatingDept ? "Adding..." : "Add department"}
						</button>
					</div>

					<div className="mt-6">
						<h3 className="text-lg font-semibold">Departments</h3>
						{deptError && (
							<p className="mt-3 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">
								{deptError}
							</p>
						)}
						{loadingDepts ? (
							<p className="mt-3 text-slate-400">Loading...</p>
						) : departments.length === 0 ? (
							<p className="mt-3 text-slate-400">No departments yet.</p>
						) : (
							<div className="mt-3 space-y-2">
								{departments.map((d) => {
									const active = d.id === selectedId
									return (
										<button
											key={d.id}
											onClick={() => setSelectedId(d.id)}
											className={`flex w-full items-center justify-between rounded-xl border px-4 py-3 text-left transition ${
											active
												? "border-indigo-400/40 bg-indigo-500/10"
												: "border-white/10 bg-white/5 hover:bg-white/10"
										}`}
										>
											<span className="font-medium">{d.name}</span>
											<span className="text-xs text-slate-400">{d.code}</span>
										</button>
									)
								})}
							</div>
						)}
					</div>
				</div>

				{/* Sections column */}
				<div>
					{selected ? (
						<SectionsPanel department={selected} />
					) : (
						<div className="rounded-2xl border border-dashed border-white/15 bg-white/5 p-6 text-slate-400">
							Select a department on the left to manage its sections.
						</div>
					)}
				</div>
			</div>
		</div>
	)
}

/* ------------------------------ Sections panel ------------------------------ */

function SectionsPanel({ department }: { department: Department }) {
	const [sections, setSections] = useState<Section[]>([])
	const [loading, setLoading] = useState(true)
	const [error, setError] = useState<string | null>(null)

	const [name, setName] = useState("")
	const [year, setYear] = useState("")
	const [creating, setCreating] = useState(false)
	const [createError, setCreateError] = useState<string | null>(null)

	const loadSections = useCallback(async () => {
		setLoading(true)
		setError(null)
		try {
			setSections(
				await api.get<Section[]>(
					`/admin/departments/${department.id}/sections`,
				),
			)
		} catch (err) {
			setError(
				err instanceof ApiError ? err.message : "Could not load sections.",
			)
		} finally {
			setLoading(false)
		}
	}, [department.id])

	useEffect(() => {
		loadSections()
	}, [loadSections])

	async function createSection() {
		if (!name.trim()) {
			setCreateError("Section name is required.")
			return
		}
		setCreating(true)
		setCreateError(null)
		try {
			const payload: Record<string, unknown> = { name: name.trim() }
			if (year.trim()) payload.year = Number(year)
			await api.post(`/admin/departments/${department.id}/sections`, payload)
			setName("")
			setYear("")
			await loadSections()
		} catch (err) {
			setCreateError(
				err instanceof ApiError ? err.message : "Could not create section.",
			)
		} finally {
			setCreating(false)
		}
	}

	return (
		<div className="rounded-2xl border border-white/10 bg-white/5 p-6">
			<h3 className="text-lg font-semibold">
				Sections in {department.name}{" "}
				<span className="text-xs text-slate-500">({department.code})</span>
			</h3>

			<div className="mt-3 grid gap-3 sm:grid-cols-2">
				<div>
					<label className="text-sm text-slate-400">Section name</label>
					<input
						value={name}
						onChange={(e) => setName(e.target.value)}
						className={inputClass}
						placeholder="A"
					/>
				</div>
				<div>
					<label className="text-sm text-slate-400">Year (optional, 1-10)</label>
					<input
						type="number"
						min={1}
						max={10}
						value={year}
						onChange={(e) => setYear(e.target.value)}
						className={inputClass}
						placeholder="2"
					/>
				</div>
			</div>
			{createError && (
				<p className="mt-3 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">
					{createError}
				</p>
			)}
			<button
				onClick={createSection}
				disabled={creating}
				className={primaryBtn}
			>
				{creating ? "Adding..." : "Add section"}
			</button>

			<div className="mt-6">
				{error && (
					<p className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">
						{error}
					</p>
				)}
				{loading ? (
					<p className="text-slate-400">Loading sections...</p>
				) : sections.length === 0 ? (
					<p className="text-slate-400">No sections yet in this department.</p>
				) : (
					<div className="space-y-2">
						{sections.map((s) => (
							<div
								key={s.id}
								className="flex items-center justify-between rounded-xl border border-white/10 bg-white/5 px-4 py-3"
							>
								<span className="font-medium">{s.name}</span>
								<span className="text-xs text-slate-400">
									{s.year ? `Year ${s.year}` : "\u2014"}
								</span>
							</div>
						))}
					</div>
				)}
			</div>
		</div>
	)
}
