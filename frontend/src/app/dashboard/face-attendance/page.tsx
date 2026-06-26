"use client"

/**
 * DEMO 1B - standalone Photo Attendance page (also the target of the DEMO 3
 * button added to the existing Attendance page).
 * Place at: src/app/dashboard/face-attendance/page.tsx
 */

import PhotoAttendancePanel from "@/components/face/PhotoAttendancePanel"

export default function PhotoAttendancePage() {
	return (
		<div className="space-y-4">
			<div>
				<h1 className="text-xl font-semibold text-gray-900">
					Photo Attendance
				</h1>
				<p className="text-sm text-gray-500">
					Upload a class photo, review the AI&apos;s present/absent
					suggestions, then confirm to mark attendance.
				</p>
			</div>
			<PhotoAttendancePanel />
		</div>
	)
}
