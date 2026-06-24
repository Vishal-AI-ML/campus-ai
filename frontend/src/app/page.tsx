/**
 * Campus AI - public landing page (App Router home route).
 *
 * Place this file at: src/app/page.tsx  (replace the default scaffold page)
 *
 * Pure server component (no client-side state), styled with Tailwind. The
 * "Get started" / "Login" buttons point at /login, which is built in a later
 * step - until then they will 404, which is expected.
 */

import Link from "next/link"
import type { Metadata } from "next"

// Route-level metadata (overrides the default title from layout.tsx).
export const metadata: Metadata = {
	title: "Campus AI - Verified Student Success & Placements",
	description:
		"Campus AI turns proof-backed student data into placements: verified skills, an AI career mentor, and an eligibility engine recruiters can trust.",
}

// Core product pillars shown in the features grid.
const features = [
	{
		icon: "\u{1F6E1}\uFE0F",
		title: "Verified Skills Moat",
		body: "Every skill and project is proof-backed, AI-scored, and mentor-verified. No more fake resumes - only data that holds up.",
	},
	{
		icon: "\u{1F916}",
		title: "AI Career Mentor",
		body: "A RAG-powered mentor that answers only from YOUR verified profile plus a curated career knowledge base. Grounded, cited, zero hallucination.",
	},
	{
		icon: "\u{1F3AF}",
		title: "Placement Eligibility Engine",
		body: "TPO posts a drive; the engine instantly decides who qualifies - explainable, criterion by criterion, from verified data only.",
	},
	{
		icon: "\u{1F4CA}",
		title: "Attendance & Academics",
		body: "Built-in attendance, results, and credit-weighted CGPA form the trusted data backbone the whole platform stands on.",
	},
]

// The verified-data pipeline, shown as a numbered "how it works" flow.
const steps = [
	{
		n: "01",
		title: "Claim with proof",
		body: "Students add skills and projects with evidence links and notes.",
	},
	{
		n: "02",
		title: "AI scores it",
		body: "The AI worker analyzes the proof and assigns a confidence score.",
	},
	{
		n: "03",
		title: "Mentor verifies",
		body: "Teachers verify or flag each claim. Only verified data ever counts.",
	},
	{
		n: "04",
		title: "Placement-ready",
		body: "Verified data powers eligibility, applications, and recruiter trust.",
	},
]

export default function HomePage() {
	return (
		<div className="min-h-screen bg-slate-950 text-slate-100">
			{/* Navigation */}
			<header className="sticky top-0 z-20 border-b border-white/10 bg-slate-950/80 backdrop-blur">
				<nav className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
					<Link href="/" className="flex items-center gap-2 font-semibold">
						<span className="grid h-8 w-8 place-items-center rounded-lg bg-gradient-to-br from-indigo-500 to-violet-500 text-sm font-bold">
							C
						</span>
						<span className="text-lg">Campus AI</span>
					</Link>
					<div className="flex items-center gap-6 text-sm">
						<a href="#features" className="hidden text-slate-300 hover:text-white sm:block">
							Features
						</a>
						<a href="#how" className="hidden text-slate-300 hover:text-white sm:block">
							How it works
						</a>
						<Link
							href="/login"
							className="rounded-lg bg-white px-4 py-2 font-medium text-slate-900 transition hover:bg-slate-200"
						>
							Login
						</Link>
					</div>
				</nav>
			</header>

			{/* Hero */}
			<section className="relative overflow-hidden">
				<div className="pointer-events-none absolute inset-0 bg-[radial-gradient(60%_50%_at_50%_0%,rgba(99,102,241,0.25),transparent)]" />
				<div className="mx-auto max-w-4xl px-6 py-24 text-center">
					<span className="inline-block rounded-full border border-white/15 bg-white/5 px-4 py-1 text-sm text-slate-300">
						The verified-data platform for campuses
					</span>
					<h1 className="mt-6 text-4xl font-bold tracking-tight sm:text-6xl">
						Turn{" "}
						<span className="bg-gradient-to-r from-indigo-400 to-violet-400 bg-clip-text text-transparent">
							verified student data
						</span>{" "}
						into placements
					</h1>
					<p className="mx-auto mt-6 max-w-2xl text-lg text-slate-300">
						Campus AI verifies every skill and project with proof, AI, and
						mentor review - then powers an eligibility engine and an AI career
						mentor recruiters and students can actually trust.
					</p>
					<div className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
						<Link
							href="/login"
							className="w-full rounded-lg bg-gradient-to-r from-indigo-500 to-violet-500 px-6 py-3 font-medium text-white transition hover:opacity-90 sm:w-auto"
						>
							Get started
						</Link>
						<a
							href="#features"
							className="w-full rounded-lg border border-white/15 px-6 py-3 font-medium text-slate-200 transition hover:bg-white/5 sm:w-auto"
						>
							Explore features
						</a>
					</div>
				</div>
			</section>

			{/* Features */}
			<section id="features" className="mx-auto max-w-6xl px-6 py-20">
				<div className="mx-auto max-w-2xl text-center">
					<h2 className="text-3xl font-bold sm:text-4xl">One platform, one source of truth</h2>
					<p className="mt-4 text-slate-300">
						Everything is built around a single principle: only verified data
						reaches resumes, recruiters, and reports.
					</p>
				</div>
				<div className="mt-12 grid gap-6 sm:grid-cols-2">
					{features.map((f) => (
						<div
							key={f.title}
							className="rounded-2xl border border-white/10 bg-white/5 p-6 transition hover:border-white/20 hover:bg-white/[0.07]"
						>
							<div className="text-3xl">{f.icon}</div>
							<h3 className="mt-4 text-xl font-semibold">{f.title}</h3>
							<p className="mt-2 text-slate-300">{f.body}</p>
						</div>
					))}
				</div>
			</section>

			{/* How it works */}
			<section id="how" className="border-y border-white/10 bg-white/[0.02]">
				<div className="mx-auto max-w-6xl px-6 py-20">
					<div className="mx-auto max-w-2xl text-center">
						<h2 className="text-3xl font-bold sm:text-4xl">How the moat works</h2>
						<p className="mt-4 text-slate-300">
							From a raw claim to placement-ready proof in four steps.
						</p>
					</div>
					<div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
						{steps.map((s) => (
							<div key={s.n} className="rounded-2xl border border-white/10 bg-slate-950 p-6">
								<div className="text-sm font-bold text-indigo-400">{s.n}</div>
								<h3 className="mt-2 text-lg font-semibold">{s.title}</h3>
								<p className="mt-2 text-sm text-slate-300">{s.body}</p>
							</div>
						))}
					</div>
				</div>
			</section>

			{/* Final CTA */}
			<section className="mx-auto max-w-4xl px-6 py-24 text-center">
				<h2 className="text-3xl font-bold sm:text-4xl">
					Ready to make your placements data-driven?
				</h2>
				<p className="mx-auto mt-4 max-w-xl text-slate-300">
					Bring verified skills, AI mentoring, and an eligibility engine to
					your campus.
				</p>
				<Link
					href="/login"
					className="mt-8 inline-block rounded-lg bg-gradient-to-r from-indigo-500 to-violet-500 px-8 py-3 font-medium text-white transition hover:opacity-90"
				>
					Get started
				</Link>
			</section>

			{/* Footer */}
			<footer className="border-t border-white/10">
				<div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-2 px-6 py-8 text-sm text-slate-400 sm:flex-row">
					<span>&copy; 2026 Campus AI</span>
					<span>Built on verified data.</span>
				</div>
			</footer>
		</div>
	)
}
