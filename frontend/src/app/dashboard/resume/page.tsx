/**
 * Campus AI - Student: AI Resume builder + ATS checker + version history.
 *
 * Place this file at: src/app/dashboard/resume/page.tsx
 *
 * Three tools on one page:
 *   1. Resume builder  -> POST /resume/generate  (Markdown from VERIFIED data;
 *                         each generate is auto-saved as a new version)
 *   2. Version history -> GET/PATCH/DELETE /resume/versions[/{id}]
 *                         (open, rename, mark primary, delete past drafts)
 *   3. ATS checker     -> POST /resume/ats-score  (resume vs job description)
 *
 * The builder uses only the student's verified skills/projects (the moat), so
 * the document never contains unproven claims. Markdown is shown as-is (with
 * copy / download) to stay dependency-free - no markdown renderer needed.
 */

"use client"

import { useCallback, useEffect, useState } from "react"
import { api, ApiError } from "@/lib/api"

type AtsResult = {
	score: number
	verdict: string
	matched_keywords: string[]
	missing_keywords: string[]
	suggestions: string[]
	provider: string
}

type ResumeVersionSummary = {
	id: number
	title: string
	target_role: string | null
	provider: string | null
	is_primary: boolean
	created_at: string
	preview: string
}

type ResumeVersionOut = ResumeVersionSummary & { markdown: string }

const inputClass =
	"mt-1 w-full rounded-lg border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-900 px-3 py-2 text-sm outline-none focus:border-indigo-400"
const primaryBtn =
	"rounded-lg bg-gradient-to-r from-indigo-500 to-violet-500 px-5 py-2.5 text-sm font-medium text-white disabled:opacity-50"
const ghostBtn =
	"rounded-lg border border-slate-200 dark:border-white/10 px-4 py-2 text-sm text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-white/10"
const chipBtn =
	"rounded-md border border-slate-200 dark:border-white/10 px-2.5 py-1 text-xs text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-white/10 disabled:opacity-50"

function scoreColor(score: number): string {
	if (score >= 75) return "text-emerald-600 dark:text-emerald-300"
	if (score >= 50) return "text-amber-600 dark:text-amber-300"
	return "text-red-300"
}

function barColor(score: number): string {
	if (score >= 75) return "bg-emerald-400"
	if (score >= 50) return "bg-amber-400"
	return "bg-red-400"
}

function formatDate(iso: string): string {
	const d = new Date(iso)
	if (Number.isNaN(d.getTime())) return iso
	return d.toLocaleString(undefined, {
		day: "2-digit",
		month: "short",
		year: "numeric",
		hour: "2-digit",
		minute: "2-digit",
	})
}

export default function ResumePage() {
	// --- Builder state ---
	const [targetRole, setTargetRole] = useState("")
	const [markdown, setMarkdown] = useState("")
	const [genLoading, setGenLoading] = useState(false)
	const [genError, setGenError] = useState<string | null>(null)
	const [activeVersionId, setActiveVersionId] = useState<number | null>(null)

	// --- Version history state ---
	const [versions, setVersions] = useState<ResumeVersionSummary[]>([])
	const [versionsLoading, setVersionsLoading] = useState(true)
	const [versionError, setVersionError] = useState<string | null>(null)
	const [busyVersionId, setBusyVersionId] = useState<number | null>(null)

	// --- ATS state ---
	const [resumeText, setResumeText] = useState("")
	const [jobDescription, setJobDescription] = useState("")
	const [ats, setAts] = useState<AtsResult | null>(null)
	const [atsLoading, setAtsLoading] = useState(false)
	const [atsError, setAtsError] = useState<string | null>(null)

	const loadVersions = useCallback(async () => {
		setVersionsLoading(true)
		setVersionError(null)
		try {
			const res = await api.get<ResumeVersionSummary[]>("/resume/versions")
			setVersions(res)
		} catch (err) {
			setVersionError(
				err instanceof ApiError
					? err.message
					: "Could not load your saved versions.",
			)
		} finally {
			setVersionsLoading(false)
		}
	}, [])

	useEffect(() => {
		void loadVersions()
	}, [loadVersions])

	async function handleGenerate() {
		setGenLoading(true)
		setGenError(null)
		try {
			const res = await api.post<{
				markdown: string
				provider: string
				version_id: number | null
			}>("/resume/generate", { target_role: targetRole.trim() || null })
			setMarkdown(res.markdown)
			setActiveVersionId(res.version_id)
			await loadVersions()
		} catch (err) {
			setGenError(
				err instanceof ApiError ? err.message : "Could not generate the resume.",
			)
		} finally {
			setGenLoading(false)
		}
	}

	async function openVersion(id: number) {
		setBusyVersionId(id)
		setVersionError(null)
		try {
			const res = await api.get<ResumeVersionOut>(`/resume/versions/${id}`)
			setMarkdown(res.markdown)
			setActiveVersionId(res.id)
			if (res.target_role) setTargetRole(res.target_role)
			window.scrollTo({ top: 0, behavior: "smooth" })
		} catch (err) {
			setVersionError(
				err instanceof ApiError ? err.message : "Could not open that version.",
			)
		} finally {
			setBusyVersionId(null)
		}
	}

	async function setPrimary(id: number) {
		setBusyVersionId(id)
		setVersionError(null)
		try {
			await api.patch<ResumeVersionOut>(`/resume/versions/${id}`, {
				is_primary: true,
			})
			await loadVersions()
		} catch (err) {
			setVersionError(
				err instanceof ApiError ? err.message : "Could not update the version.",
			)
		} finally {
			setBusyVersionId(null)
		}
	}

	async function renameVersion(id: number, current: string) {
		const next = window.prompt("Rename this resume version:", current)
		if (next === null) return
		const trimmed = next.trim()
		if (!trimmed || trimmed === current) return
		setBusyVersionId(id)
		setVersionError(null)
		try {
			await api.patch<ResumeVersionOut>(`/resume/versions/${id}`, {
				title: trimmed,
			})
			await loadVersions()
		} catch (err) {
			setVersionError(
				err instanceof ApiError ? err.message : "Could not rename the version.",
			)
		} finally {
			setBusyVersionId(null)
		}
	}

	async function deleteVersion(id: number) {
		if (!window.confirm("Delete this resume version? This cannot be undone."))
			return
		setBusyVersionId(id)
		setVersionError(null)
		try {
			await api.delete<void>(`/resume/versions/${id}`)
			if (activeVersionId === id) setActiveVersionId(null)
			await loadVersions()
		} catch (err) {
			setVersionError(
				err instanceof ApiError ? err.message : "Could not delete the version.",
			)
		} finally {
			setBusyVersionId(null)
		}
	}

	async function handleScore() {
		setAtsLoading(true)
		setAtsError(null)
		try {
			const res = await api.post<AtsResult>("/resume/ats-score", {
				resume_text: resumeText,
				job_description: jobDescription,
			})
			setAts(res)
		} catch (err) {
			setAtsError(
				err instanceof ApiError ? err.message : "Could not score the resume.",
			)
		} finally {
			setAtsLoading(false)
		}
	}

	function copyMarkdown() {
		if (markdown) navigator.clipboard?.writeText(markdown)
	}

	function downloadMarkdown() {
		const blob = new Blob([markdown], { type: "text/markdown" })
		const url = URL.createObjectURL(blob)
		const link = document.createElement("a")
		link.href = url
		link.download = "resume.md"
		link.click()
		URL.revokeObjectURL(url)
	}

	function useInAts() {
		setResumeText(markdown)
	}

	const clampedScore = ats ? Math.max(0, Math.min(100, ats.score)) : 0
	const atsBarStyle = { width: `${clampedScore}%` }

	return (
		<div className="space-y-8">
			<div>
				<h2 className="text-2xl font-bold">AI Resume + ATS</h2>
				<p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
					Build a resume from your{" "}
					<span className="text-slate-700 dark:text-slate-200">verified</span> skills & projects,
					keep a version history, then check it against any job description.
				</p>
			</div>

			{/* --- Resume builder --- */}
			<section className="rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-900 p-6">
				<h3 className="text-lg font-semibold">📄 Resume builder</h3>
				<p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
					Only verified data is used — no invented experience. Each generation
					is saved to your version history below.
				</p>
				<label className="mt-4 block text-sm text-slate-600 dark:text-slate-300">
					Target role (optional)
					<input
						className={inputClass}
						value={targetRole}
						onChange={(e) => setTargetRole(e.target.value)}
						placeholder="e.g. Backend Engineer"
					/>
				</label>
				<div className="mt-4 flex flex-wrap gap-2">
					<button
						className={primaryBtn}
						onClick={handleGenerate}
						disabled={genLoading}
					>
						{genLoading
							? "Generating..."
							: markdown
								? "Regenerate (saves new version)"
								: "Generate resume"}
					</button>
					{markdown && (
						<>
							<button className={ghostBtn} onClick={copyMarkdown}>
								Copy
							</button>
							<button className={ghostBtn} onClick={downloadMarkdown}>
								Download .md
							</button>
							<button className={ghostBtn} onClick={useInAts}>
								Use in ATS check
							</button>
						</>
					)}
				</div>
				{genError && (
					<p className="mt-3 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">
						{genError}
					</p>
				)}
				{markdown && (
					<pre className="mt-4 max-h-[28rem] overflow-auto whitespace-pre-wrap rounded-xl border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-slate-950 p-4 text-sm text-slate-700 dark:text-slate-200">
						{markdown}
					</pre>
				)}
			</section>

			{/* --- Version history --- */}
			<section className="rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-900 p-6">
				<div className="flex items-center justify-between">
					<h3 className="text-lg font-semibold">🕓 Version history</h3>
					<button
						className={chipBtn}
						onClick={() => void loadVersions()}
						disabled={versionsLoading}
					>
						{versionsLoading ? "Refreshing..." : "Refresh"}
					</button>
				</div>
				<p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
					Every resume you generate is saved here. Open an old draft, rename it,
					or mark one as your primary.
				</p>

				{versionError && (
					<p className="mt-3 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">
						{versionError}
					</p>
				)}

				{versionsLoading ? (
					<p className="mt-4 text-sm text-slate-500 dark:text-slate-400">Loading versions...</p>
				) : versions.length === 0 ? (
					<p className="mt-4 text-sm text-slate-500 dark:text-slate-400">
						No saved versions yet — generate a resume above to start your
						history.
					</p>
				) : (
					<ul className="mt-4 space-y-3">
						{versions.map((v) => {
							const isBusy = busyVersionId === v.id
							const isActive = activeVersionId === v.id
							return (
								<li
									key={v.id}
								className={`rounded-xl border p-4 ${
									isActive
										? "border-indigo-400/50 bg-indigo-500/5"
									: "border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-slate-950"
								}`}
								>
									<div className="flex flex-wrap items-center gap-2">
										<span className="font-medium text-slate-900 dark:text-slate-100">
											{v.title}
										</span>
										{v.is_primary && (
											<span className="rounded-full bg-amber-500/15 px-2 py-0.5 text-xs text-amber-600 dark:text-amber-300">
												★ Primary
											</span>
										)}
										{isActive && (
											<span className="rounded-full bg-indigo-500/15 px-2 py-0.5 text-xs text-indigo-600 dark:text-indigo-300">
												Shown above
											</span>
										)}
									</div>
									<div className="mt-1 text-xs text-slate-500 dark:text-slate-400">
										{formatDate(v.created_at)}
										{v.target_role ? ` · ${v.target_role}` : ""}
										{v.provider ? ` · ${v.provider}` : ""}
									</div>
									<p className="mt-2 line-clamp-2 text-sm text-slate-500 dark:text-slate-400">
										{v.preview}
									</p>
									<div className="mt-3 flex flex-wrap gap-2">
										<button
											className={chipBtn}
											onClick={() => void openVersion(v.id)}
											disabled={isBusy}
										>
											Open
										</button>
										<button
											className={chipBtn}
											onClick={() => void setPrimary(v.id)}
											disabled={isBusy || v.is_primary}
										>
											{v.is_primary ? "★ Primary" : "Set primary"}
										</button>
										<button
											className={chipBtn}
											onClick={() => void renameVersion(v.id, v.title)}
											disabled={isBusy}
										>
											Rename
										</button>
										<button
											className={chipBtn}
											onClick={() => void deleteVersion(v.id)}
											disabled={isBusy}
										>
											Delete
										</button>
									</div>
								</li>
							)
						})}
					</ul>
				)}
			</section>

			{/* --- ATS checker --- */}
			<section className="rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-900 p-6">
				<h3 className="text-lg font-semibold">🎯 ATS checker</h3>
				<p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
					Paste a resume + the job description to see how well they match.
				</p>
				<div className="mt-4 grid gap-4 md:grid-cols-2">
					<label className="block text-sm text-slate-600 dark:text-slate-300">
						Resume text
						<textarea
							className={`${inputClass} h-48`}
							value={resumeText}
							onChange={(e) => setResumeText(e.target.value)}
							placeholder="Paste your resume here (or generate one above and click 'Use in ATS check')."
						/>
					</label>
					<label className="block text-sm text-slate-600 dark:text-slate-300">
						Job description
						<textarea
							className={`${inputClass} h-48`}
							value={jobDescription}
							onChange={(e) => setJobDescription(e.target.value)}
							placeholder="Paste the job description here."
						/>
					</label>
				</div>
				<div className="mt-4">
					<button
						className={primaryBtn}
						onClick={handleScore}
						disabled={
							atsLoading || !resumeText.trim() || !jobDescription.trim()
						}
					>
						{atsLoading ? "Scoring..." : "Check ATS score"}
					</button>
				</div>
				{atsError && (
					<p className="mt-3 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">
						{atsError}
					</p>
				)}
				{ats && (
					<div className="mt-6 space-y-5">
						<div className="rounded-xl border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-slate-950 p-5">
							<div className="flex items-end gap-3">
								<span className={`text-4xl font-bold ${scoreColor(ats.score)}`}>
									{ats.score}
								</span>
								<span className="pb-1 text-sm text-slate-500 dark:text-slate-400">/ 100 match</span>
							</div>
							<div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
								<div
									className={`h-2 rounded-full ${barColor(ats.score)}`}
									style={atsBarStyle}
								/>
							</div>
							{ats.verdict && (
								<p className="mt-3 text-sm text-slate-700 dark:text-slate-200">{ats.verdict}</p>
							)}
						</div>

						<div className="grid gap-4 md:grid-cols-2">
							<div>
								<h4 className="text-sm font-semibold text-emerald-600 dark:text-emerald-300">
									Matched keywords
								</h4>
								<div className="mt-2 flex flex-wrap gap-2">
									{ats.matched_keywords.length ? (
										ats.matched_keywords.map((k) => (
											<span
												key={k}
												className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-xs text-emerald-600 dark:text-emerald-300"
											>
												{k}
											</span>
										))
									) : (
										<span className="text-xs text-slate-500 dark:text-slate-400">None detected.</span>
									)}
								</div>
							</div>
							<div>
								<h4 className="text-sm font-semibold text-red-300">
									Missing keywords
								</h4>
								<div className="mt-2 flex flex-wrap gap-2">
									{ats.missing_keywords.length ? (
										ats.missing_keywords.map((k) => (
											<span
												key={k}
												className="rounded-full bg-red-500/15 px-2 py-0.5 text-xs text-red-300"
											>
												{k}
											</span>
										))
									) : (
										<span className="text-xs text-slate-500 dark:text-slate-400">
											None — great coverage!
										</span>
									)}
								</div>
							</div>
						</div>

						{ats.suggestions.length > 0 && (
							<div>
								<h4 className="text-sm font-semibold text-slate-700 dark:text-slate-200">
									Suggestions
								</h4>
								<ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-600 dark:text-slate-300">
									{ats.suggestions.map((s, i) => (
										<li key={i}>{s}</li>
									))}
								</ul>
							</div>
						)}
					</div>
				)}
			</section>
		</div>
	)
}
