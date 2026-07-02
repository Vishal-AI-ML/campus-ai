"use client"

/**
 * DEMO 2 - single page with two tabs (Enroll | Take by Photo).
 * Place at: src/app/dashboard/face/page.tsx
 */

import { useState } from "react"

import FaceEnrollPanel from "@/components/face/FaceEnrollPanel"
import PhotoAttendancePanel from "@/components/face/PhotoAttendancePanel"

type Tab = "enroll" | "photo"

export default function FacePage() {
	const [tab, setTab] = useState<Tab>("enroll")

	const tabClass = (active: boolean) =>
		`rounded-md px-4 py-2 text-sm font-medium ${
			active
				? "bg-indigo-600 text-white"
				: "bg-gray-100 dark:bg-slate-800 text-gray-700 dark:text-slate-300 hover:bg-gray-200 dark:hover:bg-white/10"
		}`

	return (
		<div className="space-y-4">
			<div>
				<h1 className="text-xl font-semibold text-gray-900 dark:text-slate-100">Face Attendance</h1>
				<p className="text-sm text-gray-500 dark:text-slate-400">
					Enroll students&apos; faces and take attendance from a class photo.
				</p>
			</div>

			<div className="flex gap-2">
				<button
					type="button"
					className={tabClass(tab === "enroll")}
					onClick={() => setTab("enroll")}
				>
					Enroll
				</button>
				<button
					type="button"
					className={tabClass(tab === "photo")}
					onClick={() => setTab("photo")}
				>
					Take by Photo
				</button>
			</div>

			{tab === "enroll" ? <FaceEnrollPanel /> : <PhotoAttendancePanel />}
		</div>
	)
}
