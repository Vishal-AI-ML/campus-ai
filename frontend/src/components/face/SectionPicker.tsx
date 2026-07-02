"use client"

/**
 * Department -> Section cascading picker, shared by the face-attendance pages.
 * Place at: src/components/face/SectionPicker.tsx
 */

import { useEffect, useState } from "react"

import { api, ApiError } from "@/lib/api"

import type { Department, Section } from "./faceApi"

type Props = {
	/** Fires whenever the selected section changes (null = nothing selected). */
	onSectionChange: (sectionId: number | null, section: Section | null) => void
}

export default function SectionPicker({ onSectionChange }: Props) {
	const [departments, setDepartments] = useState<Department[]>([])
	const [sections, setSections] = useState<Section[]>([])
	const [deptId, setDeptId] = useState<number | null>(null)
	const [sectionId, setSectionId] = useState<number | null>(null)
	const [error, setError] = useState<string | null>(null)

	useEffect(() => {
		let active = true
		;(async () => {
			try {
				const data = (await api.get("/admin/departments")) as Department[]
				if (active) setDepartments(data)
			} catch (e) {
				if (active)
					setError(
						e instanceof ApiError ? e.message : "Could not load departments",
					)
			}
		})()
		return () => {
			active = false
		}
	}, [])

	async function handleDept(value: string) {
		const id = value ? Number(value) : null
		setDeptId(id)
		setSectionId(null)
		setSections([])
		onSectionChange(null, null)
		if (id === null) return
		try {
			const data = (await api.get(
				`/admin/departments/${id}/sections`,
			)) as Section[]
			setSections(data)
		} catch (e) {
			setError(e instanceof ApiError ? e.message : "Could not load sections")
		}
	}

	function handleSection(value: string) {
		const id = value ? Number(value) : null
		setSectionId(id)
		const sec = sections.find((s) => s.id === id) ?? null
		onSectionChange(id, sec)
	}

	return (
		<div className="flex flex-wrap items-end gap-3">
			<label className="flex flex-col gap-1 text-sm">
				<span className="font-medium text-gray-700 dark:text-slate-300">Department</span>
				<select
					className="rounded-md border border-gray-300 dark:border-white/15 px-3 py-2 text-sm"
					value={deptId ?? ""}
					onChange={(e) => handleDept(e.target.value)}
				>
					<option value="">Select department</option>
					{departments.map((d) => (
						<option key={d.id} value={d.id}>
							{d.code} - {d.name}
						</option>
					))}
				</select>
			</label>

			<label className="flex flex-col gap-1 text-sm">
				<span className="font-medium text-gray-700 dark:text-slate-300">Section</span>
				<select
					className="rounded-md border border-gray-300 dark:border-white/15 px-3 py-2 text-sm disabled:bg-gray-100"
					value={sectionId ?? ""}
					disabled={deptId === null}
					onChange={(e) => handleSection(e.target.value)}
				>
					<option value="">Select section</option>
					{sections.map((s) => (
						<option key={s.id} value={s.id}>
							{s.name}
							{s.year ? ` (Year ${s.year})` : ""}
						</option>
					))}
				</select>
			</label>

			{error && <p className="text-sm text-red-600">{error}</p>}
		</div>
	)
}
