"use client"

// Doubt Forum route (/dashboard/doubts). Reads /auth/me and shows the
// teacher/admin moderation panel or the student ask/browse panel by role.

import { useEffect, useState } from "react"
import { api, ApiError } from "@/lib/api"
import DoubtStudentPanel from "@/components/doubts/DoubtStudentPanel"
import DoubtTeacherPanel from "@/components/doubts/DoubtTeacherPanel"
import type { MeUser } from "@/components/doubts/doubtsApi"

export default function DoubtsPage() {
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
	if (!me) return <p className="text-sm text-gray-500 dark:text-slate-400">Loading...</p>

	const isStaff = me.role === "teacher" || me.role === "admin"

	return (
		<div className="mx-auto max-w-3xl space-y-6 p-6">
			<div>
				<h1 className="text-xl font-semibold text-gray-900 dark:text-slate-100">
					💬 Doubt Forum
				</h1>
				<p className="text-sm text-gray-500 dark:text-slate-400">
					{isStaff
						? "Browse and answer your sections' doubts, and accept the best answer."
						: "Ask doubts and get answers from your peers and teachers."}
				</p>
			</div>
			{isStaff ? (
				<DoubtTeacherPanel me={me} />
			) : (
				<DoubtStudentPanel me={me} />
			)}
		</div>
	)
}
