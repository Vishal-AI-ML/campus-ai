"use client"

// Teacher/admin Study Hub panel: pick a section, upload a material, and see /
// delete the section's existing materials.

import { useState, type FormEvent } from "react"
import { api, ApiError } from "@/lib/api"
import SectionPicker from "./SectionPicker"
import {
	CATEGORY_LABEL,
	MATERIAL_CATEGORIES,
	formatDateTime,
	type MaterialCategory,
	type MaterialOut,
	type Section,
} from "./studyHubApi"

export default function MaterialTeacherPanel() {
	const [sectionId, setSectionId] = useState<number | null>(null)
	const [materials, setMaterials] = useState<MaterialOut[]>([])
	const [loading, setLoading] = useState(false)
	const [error, setError] = useState<string | null>(null)

	// Upload-form state.
	const [title, setTitle] = useState("")
	const [description, setDescription] = useState("")
	const [category, setCategory] = useState<MaterialCategory>("notes")
	const [content, setContent] = useState("")
	const [link, setLink] = useState("")
	const [submitting, setSubmitting] = useState(false)
	const [formError, setFormError] = useState<string | null>(null)

	function loadMaterials(id: number) {
		setLoading(true)
		setError(null)
		api
			.get(`/materials?section_id=${id}`)
			.then((data) => setMaterials(data as MaterialOut[]))
			.catch((e) =>
				setError(e instanceof ApiError ? e.message : "Failed to load materials")
			)
			.finally(() => setLoading(false))
	}

	function handleSectionChange(id: number | null, _section: Section | null) {
		setSectionId(id)
		setMaterials([])
		if (id !== null) loadMaterials(id)
	}

	async function handleCreate(e: FormEvent) {
		e.preventDefault()
		if (sectionId === null) return
		if (!content.trim() && !link.trim()) {
			setFormError("Provide notes content or a resource link")
			return
		}
		setSubmitting(true)
		setFormError(null)
		try {
			await api.post("/materials", {
				section_id: sectionId,
				title: title.trim(),
				description: description.trim() || null,
				content: content.trim() || null,
				link: link.trim() || null,
				category,
			})
			setTitle("")
			setDescription("")
			setContent("")
			setLink("")
			setCategory("notes")
			loadMaterials(sectionId)
		} catch (e) {
			setFormError(
				e instanceof ApiError ? e.message : "Failed to upload material"
			)
		} finally {
			setSubmitting(false)
		}
	}

	async function handleDelete(id: number) {
		if (sectionId === null) return
		try {
			await api.delete(`/materials/${id}`)
			loadMaterials(sectionId)
		} catch (e) {
			setError(e instanceof ApiError ? e.message : "Failed to delete material")
		}
	}

	return (
		<div className="space-y-6">
			<section>
				<h2 className="mb-2 text-sm font-semibold text-gray-700 dark:text-slate-300">
					Pick a section
				</h2>
				<SectionPicker onSectionChange={handleSectionChange} />
			</section>

			{sectionId !== null ? (
				<>
					<form
						onSubmit={handleCreate}
						className="space-y-3 rounded-lg border border-gray-200 dark:border-white/10 p-4"
					>
						<h2 className="text-sm font-semibold text-gray-700 dark:text-slate-300">
							Upload a material
						</h2>
						<div className="flex flex-wrap gap-3">
							<input
								className="flex-1 rounded-md border border-gray-300 dark:border-white/15 px-3 py-2 text-sm"
								placeholder="Title"
								value={title}
								onChange={(e) => setTitle(e.target.value)}
								required
							/>
							<select
								className="rounded-md border border-gray-300 dark:border-white/15 px-3 py-2 text-sm"
								value={category}
								onChange={(e) =>
									setCategory(e.target.value as MaterialCategory)
								}
							>
								{MATERIAL_CATEGORIES.map((c) => (
									<option key={c} value={c}>
										{CATEGORY_LABEL[c]}
									</option>
								))}
							</select>
						</div>
						<input
							className="w-full rounded-md border border-gray-300 dark:border-white/15 px-3 py-2 text-sm"
							placeholder="Short description (optional)"
							value={description}
							onChange={(e) => setDescription(e.target.value)}
						/>
						<textarea
							className="w-full rounded-md border border-gray-300 dark:border-white/15 px-3 py-2 text-sm"
							placeholder="Notes content (optional)"
							rows={4}
							value={content}
							onChange={(e) => setContent(e.target.value)}
						/>
						<input
							className="w-full rounded-md border border-gray-300 dark:border-white/15 px-3 py-2 text-sm"
							placeholder="Resource link (optional, e.g. Drive/PDF/YouTube)"
							value={link}
							onChange={(e) => setLink(e.target.value)}
						/>
						{formError ? (
							<p className="text-sm text-red-600">{formError}</p>
						) : null}
						<button
							type="submit"
							disabled={submitting}
							className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
						>
							{submitting ? "Uploading..." : "Upload material"}
						</button>
					</form>

					<section className="space-y-3">
						<h2 className="text-sm font-semibold text-gray-700 dark:text-slate-300">
							Section materials
						</h2>
						{loading ? (
							<p className="text-sm text-gray-500 dark:text-slate-400">Loading...</p>
						) : error ? (
							<p className="text-sm text-red-600">{error}</p>
						) : materials.length === 0 ? (
							<p className="text-sm text-gray-500 dark:text-slate-400">No materials yet.</p>
						) : (
							<ul className="space-y-3">
								{materials.map((m) => (
									<li
										key={m.id}
									className="rounded-lg border border-gray-200 dark:border-white/10 p-4"
								>
									<div className="flex items-start justify-between gap-3">
										<div>
											<p className="font-medium text-gray-900 dark:text-slate-100">
												{m.title}{" "}
												<span className="text-xs text-gray-500 dark:text-slate-400">
													{CATEGORY_LABEL[m.category]}
												</span>
											</p>
											{m.description ? (
												<p className="text-sm text-gray-600 dark:text-slate-300">
													{m.description}
												</p>
											) : null}
											{m.content ? (
												<p className="mt-1 whitespace-pre-wrap text-sm text-gray-700 dark:text-slate-300">
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
											<p className="mt-1 text-xs text-gray-400 dark:text-slate-500">
												{formatDateTime(m.created_at)}
											</p>
										</div>
										<button
											onClick={() => handleDelete(m.id)}
											className="shrink-0 rounded-md border border-red-300 px-3 py-1 text-xs text-red-600 hover:bg-red-50"
										>
											Delete
										</button>
									</div>
								</li>
							))}
						</ul>
					)}
					</section>
				</>
			) : (
				<p className="text-sm text-gray-500 dark:text-slate-400">
					Select a department and section to manage its study materials.
				</p>
			)}
		</div>
	)
}
