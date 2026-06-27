"use client"

// Route: /dashboard/timetable
// Role-aware: teachers/admins manage a section's schedule; students view
// their own weekly timetable (read-only).
import { useEffect, useState } from "react"

import { ApiError } from "@/lib/api"
import { MeUser, getMe } from "@/components/timetable/timetableApi"
import TimetableManagerPanel from "@/components/timetable/TimetableManagerPanel"
import TimetableStudentPanel from "@/components/timetable/TimetableStudentPanel"

const ICON = "\u{1F4C5}"

export default function TimetablePage() {
  const [me, setMe] = useState<MeUser | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getMe()
      .then(setMe)
      .catch((e) =>
        setError(e instanceof ApiError ? e.message : "Failed to load profile")
      )
  }, [])

  const isManager = me?.role === "teacher" || me?.role === "admin"

  return (
    <div className="mx-auto max-w-3xl p-6">
      <h1 className="mb-1 text-2xl font-bold text-gray-900">{ICON} Timetable</h1>
      <p className="mb-6 text-sm text-gray-500">
        {isManager
          ? "Manage the weekly class schedule for a section."
          : "Your weekly class schedule."}
      </p>
      {error && <p className="text-sm text-red-600">{error}</p>}
      {!me ? (
        <p className="text-sm text-gray-500">Loading...</p>
      ) : isManager ? (
        <TimetableManagerPanel role={me.role} />
      ) : (
        <TimetableStudentPanel />
      )}
    </div>
  )
}
