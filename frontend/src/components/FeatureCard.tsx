/**
 * Campus AI - reusable marketing feature card.
 *
 * Place this file at: src/components/FeatureCard.tsx
 *
 * Renders one feature from src/lib/marketing.ts and links to its detail page.
 */

import Link from "next/link"
import type { Feature } from "@/lib/marketing"

export default function FeatureCard({ feature }: { feature: Feature }) {
	return (
		<Link
			href={`/features/${feature.slug}`}
			className="group flex flex-col rounded-2xl border border-white/10 bg-white/5 p-6 transition hover:border-indigo-400/40 hover:bg-white/10"
		>
			<div className="text-3xl">{feature.icon}</div>
			<h3 className="mt-4 text-lg font-semibold">{feature.title}</h3>
			<p className="mt-1 text-sm font-medium text-indigo-300">
				{feature.tagline}
			</p>
			<p className="mt-3 flex-1 text-sm text-slate-400">
				{feature.description}
			</p>
			<span className="mt-4 text-sm text-indigo-300 transition group-hover:text-indigo-200">
				Learn more →
			</span>
		</Link>
	)
}
