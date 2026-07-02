/**
 * Campus AI - feature detail page.
 *
 * Place this file at: src/app/features/[slug]/page.tsx
 *
 * One statically-generated, SEO-friendly page per feature in marketing.ts.
 * Unknown slugs return a 404 via notFound().
 *
 * Note (Next.js 15+/16): route `params` is async and must be awaited.
 */

import Link from "next/link"
import { notFound } from "next/navigation"
import type { Metadata } from "next"
import MarketingShell from "@/components/MarketingShell"
import FeatureCard from "@/components/FeatureCard"
import { FEATURES, getFeature } from "@/lib/marketing"

type FeatureParams = { params: Promise<{ slug: string }> }

export function generateStaticParams() {
	return FEATURES.map((feature) => ({ slug: feature.slug }))
}

export async function generateMetadata({
	params,
}: FeatureParams): Promise<Metadata> {
	const { slug } = await params
	const feature = getFeature(slug)
	if (!feature) return { title: "Feature not found — Campus AI" }
	return {
		title: `${feature.title} — Campus AI`,
		description: feature.description,
		openGraph: { title: feature.title, description: feature.description },
	}
}

export default async function FeaturePage({ params }: FeatureParams) {
	const { slug } = await params
	const feature = getFeature(slug)
	if (!feature) notFound()

	const related = FEATURES.filter((f) => f.slug !== feature.slug).slice(0, 3)

	return (
		<MarketingShell>
			{/* Hero */}
			<section className="mx-auto max-w-4xl px-6 py-20">
				<Link
					href="/#features"
					className="text-sm text-slate-500 dark:text-slate-400 transition hover:text-slate-900 dark:hover:text-white"
				>
					← All features
				</Link>
				<div className="mt-6 text-5xl">{feature.icon}</div>
				<h1 className="mt-4 text-4xl font-bold sm:text-5xl">
					{feature.title}
				</h1>
				<p className="mt-3 text-lg font-medium text-indigo-600 dark:text-indigo-300">
					{feature.tagline}
				</p>
				<p className="mt-6 max-w-2xl text-lg text-slate-600 dark:text-slate-300">
					{feature.description}
				</p>
			</section>

			{/* Highlights */}
			<section className="mx-auto max-w-4xl px-6 pb-16">
				<h2 className="text-2xl font-bold">What you get</h2>
				<div className="mt-6 grid gap-4 sm:grid-cols-2">
					{feature.highlights.map((highlight) => (
						<div
							key={highlight}
							className="flex gap-3 rounded-xl border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-900 p-4"
						>
							<span className="text-emerald-600 dark:text-emerald-300">✓</span>
							<span className="text-sm text-slate-700 dark:text-slate-200">{highlight}</span>
						</div>
					))}
				</div>
			</section>

			{/* CTA */}
			<section className="mx-auto max-w-4xl px-6 pb-16">
				<div className="rounded-3xl border border-slate-200 dark:border-white/10 bg-gradient-to-r from-indigo-500/15 to-violet-500/15 p-8 text-center">
					<h2 className="text-2xl font-bold">See {feature.title} in action</h2>
					<p className="mx-auto mt-2 max-w-xl text-slate-600 dark:text-slate-300">
						Book a walkthrough or jump straight into the platform.
					</p>
					<div className="mt-6 flex flex-wrap justify-center gap-4">
						<Link
							href="/contact"
							className="rounded-lg bg-gradient-to-r from-indigo-500 to-violet-500 px-6 py-3 text-sm font-medium text-white transition hover:opacity-90"
						>
							Request a demo
						</Link>
						<Link
							href="/login"
							className="rounded-lg border border-slate-300 dark:border-white/15 px-6 py-3 text-sm font-medium text-slate-700 dark:text-slate-200 transition hover:bg-slate-100 dark:hover:bg-white/10"
						>
							Get started
						</Link>
					</div>
				</div>
			</section>

			{/* Related features */}
			<section className="mx-auto max-w-6xl px-6 pb-20">
				<h2 className="text-2xl font-bold">Explore more</h2>
				<div className="mt-6 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
					{related.map((item) => (
						<FeatureCard key={item.slug} feature={item} />
					))}
				</div>
			</section>
		</MarketingShell>
	)
}
