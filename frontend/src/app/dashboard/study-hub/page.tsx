"use client"

// Study Hub route (/dashboard/study-hub). Reads /auth/me and shows the
// teacher/admin manage panel or the student browse panel based on role.

import { useEffect, useState } from "react"
import { api, ApiError } from "@/lib/api"
import MaterialTeacherPanel from "@/components/studyhub/MaterialTeacherPanel"
import MaterialStudentPanel from "@/components/studyhub/MaterialStudentPanel"
import type { MeUser } from "@/components/studyhub/studyHubApi"

export default function StudyHubPage() {
	const [me, setMe] = useState<MeUser | null>(null)
	const [error, setError] = useState<string | null>(null)

	useEffect(() => {
		api
			.get("/auth/me")
			.then((data) => setMe(data as MeUser))
			.catch((e) =>
				setError(e instanceof ApiError ? e.message : "Failed to load profile")
			)
	}, [])

	if (error) return <p className="text-sm text-red-600">{error}</p>
	if (!me) return <p className="text-sm text-gray-500">Loading...</p>

	const isStaff = me.role === "teacher" || me.role === "admin"

	return (
		<div className="mx-auto max-w-3xl space-y-6 p-6">
			<div>
				<h1 className="text-xl font-semibold text-gray-900">\uD83D\uDCDA Study Hub</h1>
				<p className="text-sm text-gray-500">
					{isStaff
						? "Upload and manage study materials for your sections."
						: "Browse study materials shared with your section."}
				</p>
			</div>
			{isStaff ? <MaterialTeacherPanel /> : <MaterialStudentPanel />}
		</div>
	)
}
