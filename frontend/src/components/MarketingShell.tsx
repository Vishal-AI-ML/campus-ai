/**
 * Campus AI - Marketing chrome (header + footer) wrapper.
 *
 * Place this file at: src/components/MarketingShell.tsx
 *
 * Wrap every public marketing page in <MarketingShell> so the nav and footer
 * stay consistent. Auth pages (/login, /dashboard) do NOT use this.
 */

import Link from "next/link"
import type { ReactNode } from "react"
import { MARKETING_NAV, ROLES } from "@/lib/marketing"

export default function MarketingShell({ children }: { children: ReactNode }) {
	return (
		<div className="min-h-screen bg-slate-950 text-slate-100">
			{/* Header */}
			<header className="sticky top-0 z-30 border-b border-white/10 bg-slate-950/80 backdrop-blur">
				<div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-4">
					<Link href="/" className="text-lg font-bold">
						<span className="bg-gradient-to-r from-indigo-400 to-violet-400 bg-clip-text text-transparent">
							Campus AI
						</span>
					</Link>

					<nav className="hidden items-center gap-6 text-sm text-slate-300 md:flex">
						{MARKETING_NAV.map((link) => (
							<Link
								key={link.href}
								href={link.href}
								className="transition hover:text-white"
							>
								{link.label}
							</Link>
						))}
					</nav>

					<div className="flex items-center gap-3">
						<Link
							href="/login"
							className="text-sm text-slate-300 transition hover:text-white"
						>
							Log in
						</Link>
						<Link
							href="/login"
							className="rounded-lg bg-gradient-to-r from-indigo-500 to-violet-500 px-4 py-2 text-sm font-medium text-white transition hover:opacity-90"
						>
							Get started
						</Link>
					</div>
				</div>
			</header>

			<main>{children}</main>

			{/* Footer */}
			<footer className="border-t border-white/10 bg-slate-950">
				<div className="mx-auto grid max-w-6xl gap-8 px-6 py-12 sm:grid-cols-2 md:grid-cols-4">
					<div>
						<div className="text-base font-bold">
							<span className="bg-gradient-to-r from-indigo-400 to-violet-400 bg-clip-text text-transparent">
								Campus AI
							</span>
						</div>
						<p className="mt-3 text-sm text-slate-400">
							From the first check-in to the final offer letter.
						</p>
					</div>

					<div>
						<h4 className="text-sm font-semibold text-slate-200">Product</h4>
						<ul className="mt-3 space-y-2 text-sm text-slate-400">
							<li>
								<Link href="/#features" className="hover:text-white">
									Features
								</Link>
							</li>
							<li>
								<Link href="/pricing" className="hover:text-white">
									Pricing
								</Link>
							</li>
							<li>
								<Link href="/contact" className="hover:text-white">
									Contact
								</Link>
							</li>
						</ul>
					</div>

					<div>
						<h4 className="text-sm font-semibold text-slate-200">Solutions</h4>
						<ul className="mt-3 space-y-2 text-sm text-slate-400">
							{ROLES.map((role) => (
								<li key={role.slug}>
									<Link href={`/for-${role.slug}`} className="hover:text-white">
										{role.title}
									</Link>
								</li>
							))}
						</ul>
					</div>

					<div>
						<h4 className="text-sm font-semibold text-slate-200">Get started</h4>
						<ul className="mt-3 space-y-2 text-sm text-slate-400">
							<li>
								<Link href="/login" className="hover:text-white">
									Log in
								</Link>
							</li>
							<li>
								<Link href="/contact" className="hover:text-white">
									Request a demo
								</Link>
							</li>
						</ul>
					</div>
				</div>
				<div className="border-t border-white/10 py-6 text-center text-xs text-slate-500">
					© {new Date().getFullYear()} Campus AI. All rights reserved.
				</div>
			</footer>
		</div>
	)
}
