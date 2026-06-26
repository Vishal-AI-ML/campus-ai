"use client"

// Teacher/admin doubt-forum panel: pick a section, browse its doubts, and open
// one to answer / upvote / accept (resolve).

import { useState } from "react"
import { api, ApiError } from "@/lib/api"
import SectionPicker from "./SectionPicker"
import DoubtDetail from "./DoubtDetail"
import {
	formatDateTime,
	type DoubtOut,
	type MeUser,
	type Section,
} from "./doubtsApi"

export default function DoubtTeacherPanel({ me }: { me: MeUser }) {
	const [sectionId, setSectionId] = useState<number | null>(null)
	const [doubts, setDoubts] = useState<DoubtOut[]>([])
	const [loading, setLoading] = useState(false)
	const [error, setError] = useState<string | null>(null)
	const [selected, setSelected] = useState<number | null>(null)

	function loadDoubts(id: number) {
		setLoading(true)
		setError(null)
		api
			.get(`/doubts?section_id=${id}`)
			.then((data) => setDoubts(data as DoubtOut[]))
			.catch((e) =>
				setError(e instanceof ApiError ? e.message : "Failed to load doubts")
			)
			.finally(() => setLoading(false))
	}

	function handleSectionChange(id: number | null, _section: Section | null) {
		setSectionId(id)
		setDoubts([])
		setSelected(null)
		if (id !== null) loadDoubts(id)
	}

	const statusBadge = (resolved: boolean) =>
		resolved
			? "shrink-0 rounded-full bg-green-100 px-2 py-0.5 text-xs text-green-700"
			: "shrink-0 rounded-full bg-amber-100 px-2 py-0.5 text-xs text-amber-700"

	if (selected !== null) {
		return (
			<DoubtDetail
				doubtId={selected}
				me={me}
				onBack={() => {
					setSelected(null)
					if (sectionId !== null) loadDoubts(sectionId)
				}}
				onChanged={() => {
					if (sectionId !== null) loadDoubts(sectionId)
				}}
			/>
		)
	}

	return (
		<div className="space-y-6">
			<section>
				<h2 className="mb-2 text-sm font-semibold text-gray-700">
					Pick a section
				</h2>
				<SectionPicker onSectionChange={handleSectionChange} />
			</section>

			{sectionId === null ? (
				<p className="text-sm text-gray-500">
					Select a department and section to view its doubts.
				</p>
			) : loading ? (
				<p className="text-sm text-gray-500">Loading...</p>
			) : error ? (
				<p className="text-sm text-red-600">{error}</p>
			) : doubts.length === 0 ? (
				<p className="text-sm text-gray-500">No doubts in this section yet.</p>
			) : (
				<ul className="space-y-2">
					{doubts.map((d) => (
						<li key={d.id}>
							<button
								onClick={() => setSelected(d.id)}
								className="w-full rounded-lg border border-gray-200 p-3 text-left hover:bg-gray-50"
							>
								<div className="flex items-center justify-between gap-3">
									<span className="font-medium text-gray-900">
										{d.title}
									</span>
									<span className={statusBadge(d.status === "resolved")}>
										{d.status === "resolved" ? "Resolved" : "Open"}
									</span>
								</div>
								<p className="mt-1 text-xs text-gray-500">
									{d.answer_count} answer
									{d.answer_count === 1 ? "" : "s"}
								</p>
							</button>
						</li>
					))}
				</ul>
			)}
		</div>
	)
}
