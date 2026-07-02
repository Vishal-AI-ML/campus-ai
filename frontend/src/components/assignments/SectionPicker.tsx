"use client"

import { useEffect, useState } from "react"

import { api, ApiError } from "@/lib/api"

import type { Department, Section } from "./assignmentsApi"

interface Props {
	// Fires whenever the chosen section changes (null when cleared).
	onSectionChange: (sectionId: number | null, section: Section | null) => void
}

// Department -> Section cascading dropdown, reused by the teacher panel.
export default function SectionPicker({ onSectionChange }: Props) {
	const [departments, setDepartments] = useState<Department[]>([])
	const [sections, setSections] = useState<Section[]>([])
	const [deptId, setDeptId] = useState<number | null>(null)
	const [sectionId, setSectionId] = useState<number | null>(null)
	const [error, setError] = useState<string | null>(null)

	useEffect(() => {
		api
			.get("/admin/departments")
			.then((d) => setDepartments(d as Department[]))
			.catch((e) =>
				setError(e instanceof ApiError ? e.message : "Failed to load departments"),
			)
	}, [])

	useEffect(() => {
		if (deptId === null) {
			setSections([])
			return
		}
		api
			.get(`/admin/departments/${deptId}/sections`)
			.then((d) => setSections(d as Section[]))
			.catch((e) =>
				setError(e instanceof ApiError ? e.message : "Failed to load sections"),
			)
	}, [deptId])

	return (
		<div className="space-y-2">
			{error ? <p className="text-sm text-red-400">{error}</p> : null}
			<div className="flex flex-wrap gap-3">
				<label className="flex flex-col text-xs text-slate-500 dark:text-slate-400">
					Department
					<select
						value={deptId ?? ""}
						onChange={(e) => {
							const id = e.target.value ? Number(e.target.value) : null
							setDeptId(id)
							setSectionId(null)
							onSectionChange(null, null)
						}}
						className="mt-1 rounded-md border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-900 px-3 py-2 text-sm text-slate-900 dark:text-slate-100"
					>
						<option value="">Select department</option>
						{departments.map((d) => (
							<option key={d.id} value={d.id}>
								{d.name} ({d.code})
							</option>
						))}
					</select>
				</label>
				<label className="flex flex-col text-xs text-slate-500 dark:text-slate-400">
					Section
					<select
						value={sectionId ?? ""}
						disabled={deptId === null}
						onChange={(e) => {
							const id = e.target.value ? Number(e.target.value) : null
							setSectionId(id)
							const sec = sections.find((s) => s.id === id) ?? null
							onSectionChange(id, sec)
						}}
						className="mt-1 rounded-md border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-900 px-3 py-2 text-sm text-slate-900 dark:text-slate-100 disabled:opacity-50"
					>
						<option value="">Select section</option>
						{sections.map((s) => (
							<option key={s.id} value={s.id}>
								{s.name}
								{s.year ? ` · Year ${s.year}` : ""}
							</option>
						))}
					</select>
				</label>
			</div>
		</div>
	)
}
