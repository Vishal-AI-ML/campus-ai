"use client"

// Department -> Section picker for the Study Hub.
// Self-contained copy (kept separate from other modules' pickers on purpose).
// Reads the structure from /admin/departments and /admin/departments/{id}/sections
// (both readable by any logged-in user) and reports the chosen section up.

import { useEffect, useState } from "react"
import { api, ApiError } from "@/lib/api"
import type { Department, Section } from "./studyHubApi"

type Props = {
	onSectionChange: (sectionId: number | null, section: Section | null) => void
}

export default function SectionPicker({ onSectionChange }: Props) {
	const [departments, setDepartments] = useState<Department[]>([])
	const [sections, setSections] = useState<Section[]>([])
	const [departmentId, setDepartmentId] = useState<number | null>(null)
	const [sectionId, setSectionId] = useState<number | null>(null)
	const [error, setError] = useState<string | null>(null)

	useEffect(() => {
		api
			.get("/admin/departments")
			.then((data) => setDepartments(data as Department[]))
			.catch((e) =>
				setError(
					e instanceof ApiError ? e.message : "Failed to load departments"
				)
			)
	}, [])

	useEffect(() => {
		if (departmentId === null) {
			setSections([])
			return
		}
		api
			.get(`/admin/departments/${departmentId}/sections`)
			.then((data) => setSections(data as Section[]))
			.catch((e) =>
				setError(e instanceof ApiError ? e.message : "Failed to load sections")
			)
	}, [departmentId])

	function handleDepartment(value: string) {
		const id = value ? Number(value) : null
		setDepartmentId(id)
		setSectionId(null)
		onSectionChange(null, null)
	}

	function handleSection(value: string) {
		const id = value ? Number(value) : null
		setSectionId(id)
		const section = sections.find((s) => s.id === id) ?? null
		onSectionChange(id, section)
	}

	return (
		<div className="flex flex-wrap gap-3">
			<div className="flex flex-col">
				<label className="text-xs font-medium text-gray-500">Department</label>
				<select
					className="rounded-md border border-gray-300 px-3 py-2 text-sm"
					value={departmentId ?? ""}
					onChange={(e) => handleDepartment(e.target.value)}
				>
					<option value="">Select department</option>
					{departments.map((d) => (
						<option key={d.id} value={d.id}>
							{d.name} ({d.code})
						</option>
					))}
				</select>
			</div>
			<div className="flex flex-col">
				<label className="text-xs font-medium text-gray-500">Section</label>
				<select
					className="rounded-md border border-gray-300 px-3 py-2 text-sm"
					value={sectionId ?? ""}
					onChange={(e) => handleSection(e.target.value)}
					disabled={departmentId === null}
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
			{error ? <p className="w-full text-sm text-red-600">{error}</p> : null}
		</div>
	)
}
