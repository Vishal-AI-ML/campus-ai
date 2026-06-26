/**
 * Campus AI - Student: AI Resume builder + ATS checker.
 *
 * Place this file at: src/app/dashboard/resume/page.tsx
 *
 * Two tools on one page:
 *   1. Resume builder  -> POST /resume/generate  (Markdown from VERIFIED data)
 *   2. ATS checker     -> POST /resume/ats-score  (resume vs job description)
 *
 * The builder uses only the student's verified skills/projects (the moat), so
 * the document never contains unproven claims. Markdown is shown as-is (with
 * copy / download) to stay dependency-free - no markdown renderer needed.
 */

"use client"

import { useState } from "react"
import { api, ApiError } from "@/lib/api"

type AtsResult = {
	score: number
	verdict: string
	matched_keywords: string[]
	missing_keywords: string[]
	suggestions: string[]
	provider: string
}

const inputClass =
	"mt-1 w-full rounded-lg border border-white/10 bg-slate-900 px-3 py-2 text-sm outline-none focus:border-indigo-400"
const primaryBtn =
	"rounded-lg bg-gradient-to-r from-indigo-500 to-violet-500 px-5 py-2.5 text-sm font-medium text-white disabled:opacity-50"
const ghostBtn =
	"rounded-lg border border-white/10 px-4 py-2 text-sm text-slate-200 hover:bg-white/5"

function scoreColor(score: number): string {
	if (score >= 75) return "text-emerald-300"
	if (score >= 50) return "text-amber-300"
	return "text-red-300"
}

function barColor(score: number): string {
	if (score >= 75) return "bg-emerald-400"
	if (score >= 50) return "bg-amber-400"
	return "bg-red-400"
}

export default function ResumePage() {
	// --- Builder state ---
	const [targetRole, setTargetRole] = useState("")
	const [markdown, setMarkdown] = useState("")
	const [genLoading, setGenLoading] = useState(false)
	const [genError, setGenError] = useState<string | null>(null)

	// --- ATS state ---
	const [resumeText, setResumeText] = useState("")
	const [jobDescription, setJobDescription] = useState("")
	const [ats, setAts] = useState<AtsResult | null>(null)
	const [atsLoading, setAtsLoading] = useState(false)
	const [atsError, setAtsError] = useState<string | null>(null)

	async function handleGenerate() {
		setGenLoading(true)
		setGenError(null)
		try {
			const res = await api.post<{ markdown: string; provider: string }>(
				"/resume/generate",
				{ target_role: targetRole.trim() || null },
			)
			setMarkdown(res.markdown)
		} catch (err) {
			setGenError(
				err instanceof ApiError ? err.message : "Could not generate the resume.",
			)
		} finally {
			setGenLoading(false)
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
				<p className="mt-1 text-sm text-slate-400">
					Build a resume from your{" "}
					<span className="text-slate-200">verified</span> skills & projects,
					then check it against any job description.
				</p>
			</div>

			{/* --- Resume builder --- */}
			<section className="rounded-2xl border border-white/10 bg-white/5 p-6">
				<h3 className="text-lg font-semibold">📄 Resume builder</h3>
				<p className="mt-1 text-sm text-slate-400">
					Only verified data is used — no invented experience.
				</p>
				<label className="mt-4 block text-sm text-slate-300">
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
								? "Regenerate"
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
					<pre className="mt-4 max-h-[28rem] overflow-auto whitespace-pre-wrap rounded-xl border border-white/10 bg-slate-950 p-4 text-sm text-slate-200">
						{markdown}
					</pre>
				)}
			</section>

			{/* --- ATS checker --- */}
			<section className="rounded-2xl border border-white/10 bg-white/5 p-6">
				<h3 className="text-lg font-semibold">🎯 ATS checker</h3>
				<p className="mt-1 text-sm text-slate-400">
					Paste a resume + the job description to see how well they match.
				</p>
				<div className="mt-4 grid gap-4 md:grid-cols-2">
					<label className="block text-sm text-slate-300">
						Resume text
						<textarea
							className={`${inputClass} h-48`}
							value={resumeText}
							onChange={(e) => setResumeText(e.target.value)}
							placeholder="Paste your resume here (or generate one above and click 'Use in ATS check')."
						/>
					</label>
					<label className="block text-sm text-slate-300">
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
						<div className="rounded-xl border border-white/10 bg-slate-950 p-5">
							<div className="flex items-end gap-3">
								<span className={`text-4xl font-bold ${scoreColor(ats.score)}`}>
									{ats.score}
								</span>
								<span className="pb-1 text-sm text-slate-400">/ 100 match</span>
							</div>
							<div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-white/10">
								<div
									className={`h-2 rounded-full ${barColor(ats.score)}`}
									style={atsBarStyle}
								/>
							</div>
							{ats.verdict && (
								<p className="mt-3 text-sm text-slate-200">{ats.verdict}</p>
							)}
						</div>

						<div className="grid gap-4 md:grid-cols-2">
							<div>
								<h4 className="text-sm font-semibold text-emerald-300">
									Matched keywords
								</h4>
								<div className="mt-2 flex flex-wrap gap-2">
									{ats.matched_keywords.length ? (
										ats.matched_keywords.map((k) => (
											<span
												key={k}
												className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-xs text-emerald-300"
											>
												{k}
											</span>
										))
									) : (
										<span className="text-xs text-slate-500">None detected.</span>
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
										<span className="text-xs text-slate-500">
											None — great coverage!
										</span>
									)}
								</div>
							</div>
						</div>

						{ats.suggestions.length > 0 && (
							<div>
								<h4 className="text-sm font-semibold text-slate-200">
									Suggestions
								</h4>
								<ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-300">
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
