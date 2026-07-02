"use client"

/**
 * DEMO 1A - standalone Face Enrollment page.
 * Place at: src/app/dashboard/face-enroll/page.tsx
 */

import FaceEnrollPanel from "@/components/face/FaceEnrollPanel"

export default function FaceEnrollPage() {
	return (
		<div className="space-y-4">
			<div>
				<h1 className="text-xl font-semibold text-gray-900 dark:text-slate-100">Face Enrollment</h1>
				<p className="text-sm text-gray-500 dark:text-slate-400">
					Register each student&apos;s reference face so the class photo can
					match them later.
				</p>
			</div>
			<FaceEnrollPanel />
		</div>
	)
}
