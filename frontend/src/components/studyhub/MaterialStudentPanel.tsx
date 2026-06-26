"use client"

// Student Study Hub panel: read-only list of materials shared with the
// logged-in student's own section (backend scopes this via /materials/me).

import { useEffect, useState } from "react"
import { api, ApiError } from "@/lib/api"
import { CATEGORY_LABEL, formatDateTime, type MaterialOut } from "./studyHubApi"

export default function MaterialStudentPanel() {
	const [materials, setMaterials] = useState<MaterialOut[]>([])
	const [loading, setLoading] = useState(true)
	const [error, setError] = useState<string | null>(null)

	useEffect(() => {
		api
			.get("/materials/me")
			.then((data) => setMaterials(data as MaterialOut[]))
			.catch((e) =>
				setError(e instanceof ApiError ? e.message : "Failed to load materials")
			)
			.finally(() => setLoading(false))
	}, [])

	if (loading) return <p className="text-sm text-gray-500">Loading...</p>
	if (error) return <p className="text-sm text-red-600">{error}</p>
	if (materials.length === 0)
		return (
			<p className="text-sm text-gray-500">
				No study materials shared with your section yet.
			</p>
		)

	return (
		<ul className="space-y-3">
			{materials.map((m) => (
				<li key={m.id} className="rounded-lg border border-gray-200 p-4">
					<p className="font-medium text-gray-900">
						{m.title}{" "}
						<span className="text-xs text-gray-500">
							{CATEGORY_LABEL[m.category]}
						</span>
					</p>
					{m.description ? (
						<p className="text-sm text-gray-600">{m.description}</p>
					) : null}
					{m.content ? (
						<p className="mt-1 whitespace-pre-wrap text-sm text-gray-700">
							{m.content}
						</p>
					) : null}
					{m.link ? (
						<a
							href={m.link}
							target="_blank"
							rel="noopener noreferrer"
							className="mt-1 inline-block text-sm text-blue-600 underline"
						>
							Open resource
						</a>
					) : null}
					<p className="mt-1 text-xs text-gray-400">
						{formatDateTime(m.created_at)}
					</p>
				</li>
			))}
		</ul>
	)
}
