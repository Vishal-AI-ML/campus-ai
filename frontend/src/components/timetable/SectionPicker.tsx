"use client"

// Department -> Section picker, shared by the Timetable manager panel.
import { useEffect, useState } from "react"

import { ApiError } from "@/lib/api"
import {
  Department,
  Section,
  listDepartments,
  listSections,
} from "./timetableApi"

type Props = {
  onSection: (sectionId: number | null) => void
}

export default function SectionPicker({ onSection }: Props) {
  const [departments, setDepartments] = useState<Department[]>([])
  const [sections, setSections] = useState<Section[]>([])
  const [deptId, setDeptId] = useState<number | "">("")
  const [sectionId, setSectionId] = useState<number | "">("")
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    listDepartments()
      .then(setDepartments)
      .catch((e) =>
        setError(e instanceof ApiError ? e.message : "Failed to load departments")
      )
  }, [])

  useEffect(() => {
    if (deptId === "") {
      setSections([])
      setSectionId("")
      onSection(null)
      return
    }
    listSections(Number(deptId))
      .then(setSections)
      .catch((e) =>
        setError(e instanceof ApiError ? e.message : "Failed to load sections")
      )
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [deptId])

  function onSectionChange(value: string) {
    const id = value === "" ? "" : Number(value)
    setSectionId(id)
    onSection(id === "" ? null : id)
  }

  return (
    <div className="flex flex-wrap gap-3">
      <select
        value={deptId}
        onChange={(e) =>
          setDeptId(e.target.value === "" ? "" : Number(e.target.value))
        }
        className="rounded border border-gray-300 dark:border-white/15 px-2 py-1 text-sm"
      >
        <option value="">Select department</option>
        {departments.map((d) => (
          <option key={d.id} value={d.id}>
            {d.name} ({d.code})
          </option>
        ))}
      </select>
      <select
        value={sectionId}
        onChange={(e) => onSectionChange(e.target.value)}
        disabled={deptId === ""}
        className="rounded border border-gray-300 dark:border-white/15 px-2 py-1 text-sm disabled:opacity-50"
      >
        <option value="">Select section</option>
        {sections.map((s) => (
          <option key={s.id} value={s.id}>
            {s.name}
            {s.year ? ` - Year ${s.year}` : ""}
          </option>
        ))}
      </select>
      {error && <span className="text-sm text-red-600">{error}</span>}
    </div>
  )
}
