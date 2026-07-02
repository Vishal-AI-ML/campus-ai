/**
 * Campus AI - shared role landing page (used by /for-[role] routes).
 *
 * Place this file at: src/components/RoleLanding.tsx
 *
 * Next.js does not allow a mixed static+dynamic segment like `for-[role]`, so
 * each role has a tiny static route that renders <RoleLanding slug=... />.
 */

import Link from "next/link"
import { notFound } from "next/navigation"
import type { Metadata } from "next"
import MarketingShell from "@/components/MarketingShell"
import { ROLES, getRole } from "@/lib/marketing"

/** Helper so each route file can export consistent metadata. */
export function roleMetadata(slug: string): Metadata {
	const role = getRole(slug)
	if (!role) return { title: "Campus AI" }
	return {
		title: `${role.title} — Campus AI`,
		description: role.pitch,
		openGraph: { title: role.title, description: role.pitch },
	}
}

export default function RoleLanding({ slug }: { slug: string }) {
	const role = getRole(slug)
	if (!role) notFound()

	const otherRoles = ROLES.filter((r) => r.slug !== role.slug)

	return (
		<MarketingShell>
			{/* Hero */}
			<section className="mx-auto max-w-4xl px-6 py-20">
				<Link
					href="/"
					className="text-sm text-slate-500 dark:text-slate-400 transition hover:text-slate-900 dark:hover:text-white"
				>
					← Home
				</Link>
				<div className="mt-6 text-5xl">{role.emoji}</div>
				<h1 className="mt-4 text-4xl font-bold sm:text-5xl">{role.title}</h1>
				<p className="mt-4 max-w-2xl text-lg text-slate-600 dark:text-slate-300">{role.pitch}</p>
				<div className="mt-8 flex flex-wrap gap-4">
					<Link
						href="/login"
						className="rounded-lg bg-gradient-to-r from-indigo-500 to-violet-500 px-6 py-3 text-sm font-medium text-white transition hover:opacity-90"
					>
						Get started
					</Link>
					<Link
						href="/contact"
						className="rounded-lg border border-slate-300 dark:border-white/15 px-6 py-3 text-sm font-medium text-slate-700 dark:text-slate-200 transition hover:bg-slate-100 dark:hover:bg-white/10"
					>
						Request a demo
					</Link>
				</div>
			</section>

			{/* What they get */}
			<section className="mx-auto max-w-4xl px-6 pb-16">
				<h2 className="text-2xl font-bold">What you can do</h2>
				<div className="mt-6 grid gap-4 sm:grid-cols-2">
					{role.points.map((point) => (
						<div
							key={point}
							className="flex gap-3 rounded-xl border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-900 p-4"
						>
							<span className="text-emerald-600 dark:text-emerald-300">✓</span>
							<span className="text-sm text-slate-700 dark:text-slate-200">{point}</span>
						</div>
					))}
				</div>
			</section>

			{/* Other roles */}
			<section className="mx-auto max-w-6xl px-6 pb-20">
				<h2 className="text-2xl font-bold">Built for every role</h2>
				<div className="mt-6 grid gap-6 sm:grid-cols-3">
					{otherRoles.map((other) => (
						<Link
							key={other.slug}
							href={`/for-${other.slug}`}
							className="group rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-900 p-6 transition hover:border-indigo-400/40 hover:bg-slate-100 dark:hover:bg-white/10"
						>
							<div className="text-3xl">{other.emoji}</div>
							<h3 className="mt-3 text-lg font-semibold">{other.title}</h3>
							<p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{other.pitch}</p>
							<span className="mt-3 inline-block text-sm text-indigo-600 dark:text-indigo-300 group-hover:text-indigo-700">
								Learn more →
							</span>
						</Link>
					))}
				</div>
			</section>
		</MarketingShell>
	)
}
