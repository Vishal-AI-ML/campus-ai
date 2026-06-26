"use client"

import { useEffect, useState } from "react"

import { api, ApiError } from "@/lib/api"

import AssignmentStudentPanel from "@/components/assignments/AssignmentStudentPanel"
import AssignmentTeacherPanel from "@/components/assignments/AssignmentTeacherPanel"
import type { MeUser } from "@/components/assignments/assignmentsApi"

// Role-aware Assignments page: staff get the create/grade panel, students get
// the submit/grade-view panel. Role is read from /auth/me so we do not depend
// on the auth context shape.
export default function AssignmentsPage() {
	const [me, setMe] = useState<MeUser | null>(null)
	const [error, setError] = useState<string | null>(null)

	useEffect(() => {
		api
			.get("/auth/me")
			.then((d) => setMe(d as MeUser))
			.catch((e) =>
				setError(e instanceof ApiError ? e.message : "Failed to load profile"),
			)
	}, [])

	const isStaff = me?.role === "teacher" || me?.role === "admin"

	return (
		<div className="mx-auto max-w-3xl space-y-6 p-6">
			<header>
				<h1 className="text-xl font-semibold text-white">📝 Assignments</h1>
				<p className="mt-1 text-sm text-white/60">
					{isStaff
						? "Create assignments for a section and grade student submissions."
						: "View your assignments, submit your work, and see your grades."}
				</p>
			</header>

			{error ? (
				<p className="rounded-md bg-red-500/10 px-3 py-2 text-sm text-red-400">
					{error}
				</p>
			) : null}

			{!me ? (
				<p className="text-sm text-white/60">Loading…</p>
			) : isStaff ? (
				<AssignmentTeacherPanel />
			) : (
				<AssignmentStudentPanel />
			)}
		</div>
	)
}
