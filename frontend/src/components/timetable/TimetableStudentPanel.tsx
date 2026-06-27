"use client"

// Student panel: read-only weekly timetable for the student's own section.
import { useEffect, useState } from "react"

import { ApiError } from "@/lib/api"
import { DAYS, TimetableEntry, formatTime, myTimetable } from "./timetableApi"

export default function TimetableStudentPanel() {
  const [entries, setEntries] = useState<TimetableEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    myTimetable()
      .then(setEntries)
      .catch((e) =>
        setError(e instanceof ApiError ? e.message : "Failed to load timetable")
      )
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <p className="text-sm text-gray-500">Loading...</p>
  if (error) return <p className="text-sm text-red-600">{error}</p>
  if (entries.length === 0) {
    return (
      <p className="text-sm text-gray-500">
        No classes scheduled yet. If you have not been assigned to a section,
        ask your admin.
      </p>
    )
  }

  return (
    <div className="space-y-4">
      {DAYS.map((dayName, idx) => {
        const dayEntries = entries
          .filter((e) => e.day_of_week === idx)
          .sort((a, b) => a.start_time.localeCompare(b.start_time))
        if (dayEntries.length === 0) return null
        return (
          <div key={idx}>
            <h3 className="mb-2 text-xs font-bold uppercase tracking-wide text-gray-500">
              {dayName}
            </h3>
            <ul className="space-y-2">
              {dayEntries.map((e) => (
                <li
                  key={e.id}
                  className="rounded border border-gray-200 px-3 py-2"
                >
                  <span className="font-medium text-gray-800">
                    {formatTime(e.start_time)} - {formatTime(e.end_time)}
                  </span>
                  {e.subject_name && (
                    <span className="ml-2 text-gray-700">{e.subject_name}</span>
                  )}
                  <span className="ml-2 text-sm text-gray-500">
                    {e.room ? `Room: ${e.room}` : ""}
                    {e.teacher_name ? ` - ${e.teacher_name}` : ""}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )
      })}
    </div>
  )
}
