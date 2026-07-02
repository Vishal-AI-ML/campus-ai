/**
 * Campus AI - public Home / landing page.
 *
 * Place this file at: src/app/page.tsx  (REPLACES the existing landing page)
 *
 * Hero -> embedded product tour -> Verify/Build/Place story -> 9 feature cards
 * -> role sections -> CTA. Driven by src/lib/marketing.ts.
 */

import Link from "next/link"
import type { Metadata } from "next"
import MarketingShell from "@/components/MarketingShell"
import FeatureCard from "@/components/FeatureCard"
import ProductTour from "@/components/landing/ProductTour"
import { FEATURES, ROLES } from "@/lib/marketing"

export const metadata: Metadata = {
	title: "Campus AI — From the first check-in to the final offer letter",
	description:
		"Campus AI turns everyday campus data into a verified student profile, powering attendance, skills, resumes and placements on one platform.",
	openGraph: {
		title: "Campus AI",
		description:
			"The verified student-success and placement platform for modern institutes.",
		type: "website",
	},
}

const STEPS = [
	{
		label: "Verify",
		icon: "🛡️",
		text: "Capture real, verified data — attendance, skills, projects — scored by AI and confirmed by mentors.",
	},
	{
		label: "Build",
		icon: "🤖",
		text: "Turn that verified data into ATS-ready resumes and grounded AI career guidance.",
	},
	{
		label: "Place",
		icon: "🏢",
		text: "Match verified, ranked candidates to the right drives — from eligibility to offer letter.",
	},
]

export default function HomePage() {
	return (
		<MarketingShell>
			{/* Hero */}
			<section className="relative overflow-hidden">
				<div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-indigo-500/10 via-transparent to-transparent" />
				<div className="mx-auto max-w-4xl px-6 py-24 text-center">
					<span className="inline-block rounded-full border border-black/10 dark:border-white/15 bg-black/5 dark:bg-white/10 px-4 py-1 text-xs text-slate-600 dark:text-slate-300">
						Student success & placement platform
					</span>
					<h1 className="mt-6 text-4xl font-bold leading-tight sm:text-6xl">
						From the first check-in to the{" "}
						<span className="bg-gradient-to-r from-indigo-500 to-violet-500 bg-clip-text text-transparent">
							final offer letter
						</span>
						.
					</h1>
					<p className="mx-auto mt-6 max-w-2xl text-lg text-slate-600 dark:text-slate-300">
						Campus AI turns everyday campus data into a verified student
						profile — powering attendance, skills, resumes and placements on
						one platform.
					</p>
					<div className="mt-10 flex flex-wrap justify-center gap-4">
						<Link
							href="#demo"
							className="rounded-lg bg-gradient-to-r from-indigo-500 to-violet-500 px-6 py-3 text-sm font-medium text-white transition hover:opacity-90"
						>
							▶ Watch live demo
						</Link>
						<Link
							href="/login"
							className="rounded-lg border border-slate-300 dark:border-white/15 px-6 py-3 text-sm font-medium text-slate-700 dark:text-slate-200 transition hover:bg-slate-100 dark:hover:bg-white/10"
						>
							Open dashboard
						</Link>
					</div>
				</div>
			</section>

			{/* Embedded product tour */}
			<ProductTour />

			{/* Verify -> Build -> Place story */}
			<section className="mx-auto max-w-6xl px-6 py-16">
				<div className="grid gap-6 md:grid-cols-3">
					{STEPS.map((step, index) => (
						<div
							key={step.label}
							className="rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-900 p-6 shadow-sm"
						>
							<div className="flex items-center gap-3">
								<span className="text-2xl">{step.icon}</span>
								<span className="text-xs text-slate-500 dark:text-slate-400">
									Step {index + 1}
								</span>
							</div>
							<h3 className="mt-3 text-xl font-semibold">{step.label}</h3>
							<p className="mt-2 text-sm text-slate-500 dark:text-slate-400">{step.text}</p>
						</div>
					))}
				</div>
			</section>

			{/* Features grid */}
			<section id="features" className="mx-auto max-w-6xl scroll-mt-20 px-6 py-16">
				<div className="text-center">
					<h2 className="text-3xl font-bold">One platform, the whole journey</h2>
					<p className="mx-auto mt-3 max-w-2xl text-slate-500 dark:text-slate-400">
						Nine modules that work together on a single source of verified
						truth.
					</p>
				</div>
				<div className="mt-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
					{FEATURES.map((feature) => (
						<FeatureCard key={feature.slug} feature={feature} />
					))}
				</div>
			</section>

			{/* Role sections */}
			<section className="mx-auto max-w-6xl px-6 py-16">
				<div className="text-center">
					<h2 className="text-3xl font-bold">Built for every role on campus</h2>
					<p className="mx-auto mt-3 max-w-2xl text-slate-500 dark:text-slate-400">
						Students, teachers, TPOs and admins — each gets a focused
						experience.
					</p>
				</div>
				<div className="mt-10 grid gap-6 sm:grid-cols-2">
					{ROLES.map((role) => (
						<div
							key={role.slug}
							className="rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-900 p-6 shadow-sm"
						>
							<div className="flex items-center gap-3">
								<span className="text-2xl">{role.emoji}</span>
								<h3 className="text-xl font-semibold">{role.title}</h3>
							</div>
							<p className="mt-2 text-sm text-indigo-500">{role.pitch}</p>
							<ul className="mt-4 space-y-2 text-sm text-slate-600 dark:text-slate-300">
								{role.points.map((point) => (
									<li key={point} className="flex gap-2">
										<span className="text-emerald-500">✓</span>
										{point}
									</li>
								))}
							</ul>
							<Link
								href={`/for-${role.slug}`}
								className="mt-5 inline-block text-sm text-indigo-500 hover:text-indigo-400"
							>
								Learn more →
							</Link>
						</div>
					))}
				</div>
			</section>

			{/* Final CTA */}
			<section className="mx-auto max-w-4xl px-6 py-20">
				<div className="rounded-3xl border border-indigo-200 dark:border-indigo-500/40 bg-gradient-to-r from-indigo-500/10 to-violet-500/10 p-10 text-center">
					<h2 className="text-3xl font-bold">
						Ready to build your campus's verified advantage?
					</h2>
					<p className="mx-auto mt-3 max-w-xl text-slate-600 dark:text-slate-300">
						See how Campus AI connects attendance, skills and placements on one
						platform.
					</p>
					<div className="mt-8 flex flex-wrap justify-center gap-4">
						<Link
							href="#demo"
							className="rounded-lg bg-gradient-to-r from-indigo-500 to-violet-500 px-6 py-3 text-sm font-medium text-white transition hover:opacity-90"
						>
							▶ Watch live demo
						</Link>
						<Link
							href="/login"
							className="rounded-lg border border-slate-300 dark:border-white/15 px-6 py-3 text-sm font-medium text-slate-700 dark:text-slate-200 transition hover:bg-slate-100 dark:hover:bg-white/10"
						>
							Open dashboard
						</Link>
					</div>
				</div>
			</section>
		</MarketingShell>
	)
}
