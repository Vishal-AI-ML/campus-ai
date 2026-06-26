/**
 * Campus AI - public Pricing page.
 *
 * Place this file at: src/app/pricing/page.tsx
 *
 * Static, SEO-friendly. Tiers are defined inline (marketing content); swap to a
 * CMS later if needed.
 */

import Link from "next/link"
import type { Metadata } from "next"
import MarketingShell from "@/components/MarketingShell"

export const metadata: Metadata = {
	title: "Pricing — Campus AI",
	description:
		"Simple plans for institutes of every size, from a single department to a multi-campus group.",
}

type Tier = {
	name: string
	price: string
	cadence: string
	tagline: string
	features: string[]
	cta: { label: string; href: string }
	popular?: boolean
}

const TIERS: Tier[] = [
	{
		name: "Starter",
		price: "Free",
		cadence: "pilot",
		tagline: "For a single department getting started.",
		features: [
			"Up to 200 students",
			"Attendance & academics",
			"Verified skills & projects",
			"Email support",
		],
		cta: { label: "Get started", href: "/login" },
	},
	{
		name: "Growth",
		price: "Custom",
		cadence: "per institute",
		tagline: "For growing institutes that want the full loop.",
		features: [
			"Up to 2,000 students",
			"Everything in Starter",
			"AI Resume + Career Mentor",
			"Placement drives & eligibility",
			"Analytics dashboards",
			"Priority support",
		],
		cta: { label: "Request a demo", href: "/contact" },
		popular: true,
	},
	{
		name: "Institute",
		price: "Custom",
		cadence: "multi-campus",
		tagline: "For large or multi-campus groups.",
		features: [
			"Unlimited students",
			"Multi-tenant & SSO",
			"Recruiter portal",
			"Audit log & governance",
			"Dedicated success manager",
			"SLA & security review",
		],
		cta: { label: "Contact sales", href: "/contact" },
	},
]

export default function PricingPage() {
	return (
		<MarketingShell>
			<section className="mx-auto max-w-4xl px-6 py-20 text-center">
				<h1 className="text-4xl font-bold sm:text-5xl">
					Pricing that scales with your campus
				</h1>
				<p className="mx-auto mt-4 max-w-2xl text-lg text-slate-300">
					Start with a free pilot. Upgrade as more departments come on board.
				</p>
			</section>

			<section className="mx-auto max-w-6xl px-6 pb-20">
				<div className="grid gap-6 lg:grid-cols-3">
					{TIERS.map((tier) => (
						<div
							key={tier.name}
							className={`flex flex-col rounded-2xl border p-6 ${
								tier.popular
									? "border-indigo-400/50 bg-indigo-500/10"
									: "border-white/10 bg-white/5"
							}`}
						>
							{tier.popular && (
								<span className="mb-3 inline-block w-fit rounded-full bg-indigo-500/20 px-3 py-1 text-xs text-indigo-200">
									Most popular
								</span>
							)}
							<h3 className="text-xl font-semibold">{tier.name}</h3>
							<p className="mt-1 text-sm text-slate-400">{tier.tagline}</p>
							<div className="mt-5 flex items-baseline gap-2">
								<span className="text-3xl font-bold">{tier.price}</span>
								<span className="text-sm text-slate-400">{tier.cadence}</span>
							</div>
							<ul className="mt-6 flex-1 space-y-2 text-sm text-slate-300">
								{tier.features.map((item) => (
									<li key={item} className="flex gap-2">
										<span className="text-emerald-400">✓</span>
										{item}
									</li>
								))}
							</ul>
							<Link
								href={tier.cta.href}
								className={`mt-6 rounded-lg px-5 py-2.5 text-center text-sm font-medium transition ${
									tier.popular
										? "bg-gradient-to-r from-indigo-500 to-violet-500 text-white hover:opacity-90"
										: "border border-white/15 text-slate-200 hover:bg-white/5"
								}`}
							>
								{tier.cta.label}
							</Link>
						</div>
					))}
				</div>

				<p className="mt-10 text-center text-sm text-slate-400">
					Need something specific?{" "}
					<Link href="/contact" className="text-indigo-300 hover:text-indigo-200">
						Talk to us
					</Link>
					.
				</p>
			</section>
		</MarketingShell>
	)
}
