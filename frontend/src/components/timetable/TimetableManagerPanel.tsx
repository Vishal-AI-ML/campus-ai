"use client"

// Staff (teacher/admin) panel: pick a section, view its weekly grid, and
// add / delete class slots. Teachers also see their own teaching schedule.
import { FormEvent, useEffect, useState } from "react"

import { ApiError } from "@/lib/api"
import SectionPicker from "./SectionPicker"
import {
  DAYS,
  TimetableEntry,
  createEntry,
  deleteEntry,
  formatTime,
  listSectionTimetable,
  myTeaching,
} from "./timetableApi"

function WeekGrid({
  entries,
  onDelete,
}: {
  entries: TimetableEntry[]
  onDelete?: (id: number) => void
}) {
  if (entries.length === 0) {
    return <p className="text-sm text-gray-500">No classes scheduled.</p>
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
                  className="flex items-center justify-between rounded border border-gray-200 px-3 py-2"
                >
                  <div>
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
                  </div>
                  {onDelete && (
                    <button
                      onClick={() => onDelete(e.id)}
                      className="text-sm text-red-600 hover:underline"
                    >
                      Delete
                    </button>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )
      })}
    </div>
  )
}

export default function TimetableManagerPanel({ role }: { role: string }) {
  const [sectionId, setSectionId] = useState<number | null>(null)
  const [entries, setEntries] = useState<TimetableEntry[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [day, setDay] = useState(0)
  const [start, setStart] = useState("09:00")
  const [end, setEnd] = useState("10:00")
  const [room, setRoom] = useState("")
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  const [teaching, setTeaching] = useState<TimetableEntry[]>([])

  function load(id: number) {
    setLoading(true)
    setError(null)
    listSectionTimetable(id)
      .then(setEntries)
      .catch((e) =>
        setError(e instanceof ApiError ? e.message : "Failed to load timetable")
      )
      .finally(() => setLoading(false))
  }

  function loadTeaching() {
    if (role !== "teacher") return
    myTeaching()
      .then(setTeaching)
      .catch(() => {})
  }

  useEffect(() => {
    if (sectionId != null) load(sectionId)
    else setEntries([])
  }, [sectionId])

  useEffect(() => {
    loadTeaching()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [role])

  async function onAdd(e: FormEvent) {
    e.preventDefault()
    if (sectionId == null) {
      setFormError("Pick a section first")
      return
    }
    setSaving(true)
    setFormError(null)
    try {
      await createEntry({
        section_id: sectionId,
        day_of_week: day,
        start_time: start,
        end_time: end,
        room: room || null,
      })
      setRoom("")
      load(sectionId)
      loadTeaching()
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "Failed to add slot")
    } finally {
      setSaving(false)
    }
  }

  async function onDelete(id: number) {
    try {
      await deleteEntry(id)
      if (sectionId != null) load(sectionId)
      loadTeaching()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to delete slot")
    }
  }

  return (
    <div className="space-y-6">
      <div className="rounded-lg border border-gray-200 p-4">
        <h2 className="mb-3 text-sm font-semibold text-gray-700">
          Select a section
        </h2>
        <SectionPicker onSection={setSectionId} />
      </div>

      {sectionId != null && (
        <form
          onSubmit={onAdd}
          className="space-y-3 rounded-lg border border-gray-200 p-4"
        >
          <h2 className="text-sm font-semibold text-gray-700">Add a class slot</h2>
          {formError && <p className="text-sm text-red-600">{formError}</p>}
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <label className="text-sm">
              <span className="block text-gray-600">Day</span>
              <select
                value={day}
                onChange={(e) => setDay(Number(e.target.value))}
                className="mt-1 w-full rounded border border-gray-300 px-2 py-1"
              >
                {DAYS.map((d, i) => (
                  <option key={i} value={i}>
                    {d}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-sm">
              <span className="block text-gray-600">Start</span>
              <input
                type="time"
                value={start}
                onChange={(e) => setStart(e.target.value)}
                className="mt-1 w-full rounded border border-gray-300 px-2 py-1"
              />
            </label>
            <label className="text-sm">
              <span className="block text-gray-600">End</span>
              <input
                type="time"
                value={end}
                onChange={(e) => setEnd(e.target.value)}
                className="mt-1 w-full rounded border border-gray-300 px-2 py-1"
              />
            </label>
            <label className="text-sm">
              <span className="block text-gray-600">Room</span>
              <input
                value={room}
                onChange={(e) => setRoom(e.target.value)}
                placeholder="Room 101"
                className="mt-1 w-full rounded border border-gray-300 px-2 py-1"
              />
            </label>
          </div>
          <button
            type="submit"
            disabled={saving}
            className="rounded bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
          >
            {saving ? "Adding..." : "Add slot"}
          </button>
        </form>
      )}

      {error && <p className="text-sm text-red-600">{error}</p>}

      {sectionId != null &&
        (loading ? (
          <p className="text-sm text-gray-500">Loading...</p>
        ) : (
          <div className="rounded-lg border border-gray-200 p-4">
            <h2 className="mb-3 text-sm font-semibold text-gray-700">
              Weekly timetable
            </h2>
            <WeekGrid entries={entries} onDelete={onDelete} />
          </div>
        ))}

      {role === "teacher" && teaching.length > 0 && (
        <div className="rounded-lg border border-gray-200 p-4">
          <h2 className="mb-3 text-sm font-semibold text-gray-700">
            My teaching schedule
          </h2>
          <WeekGrid entries={teaching} />
        </div>
      )}
    </div>
  )
}
