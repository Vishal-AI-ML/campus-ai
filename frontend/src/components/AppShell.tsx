/**
 * Campus AI - authenticated app shell (sidebar + topbar layout).
 *
 * Place this file at: src/components/AppShell.tsx
 *
 * Renders a role-aware sidebar (links from NAV_BY_ROLE), a topbar with the
 * signed-in user + logout, and the page content. Must be used inside
 * <AuthProvider> (it reads the user from useCurrentUser).
 */

"use client"

import Link from "next/link"
import { usePathname, useRouter } from "next/navigation"
import { clearToken } from "@/lib/api"
import { useCurrentUser, NAV_BY_ROLE } from "@/lib/auth"

export default function AppShell({ children }: { children: React.ReactNode }) {
	const router = useRouter()
	const pathname = usePathname()
	const { user, loading } = useCurrentUser()

	// While the provider is loading (or redirecting), show a simple splash.
	if (loading || !user) {
		return (
			<div className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-400">
				<p>Loading...</p>
			</div>
		)
	}

	const nav = NAV_BY_ROLE[user.role] ?? []

	function isActive(href: string): boolean {
		// "Overview" (/dashboard) should only match exactly; others match prefix.
		return href === "/dashboard"
			? pathname === "/dashboard"
			: pathname.startsWith(href)
	}

	function handleLogout() {
		clearToken()
		router.replace("/login")
	}

	return (
		<div className="flex min-h-screen bg-slate-950 text-slate-100">
			{/* Sidebar */}
			<aside className="flex w-60 flex-col border-r border-white/10 bg-slate-900/50">
				<div className="flex items-center gap-2 px-5 py-5 font-semibold">
					<span className="grid h-8 w-8 place-items-center rounded-lg bg-gradient-to-br from-indigo-500 to-violet-500 text-sm font-bold">
						C
					</span>
					<span>Campus AI</span>
				</div>

				<nav className="flex-1 space-y-1 px-3 py-2">
					{nav.map((item) => (
						<Link
							key={item.href}
							href={item.href}
							className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition ${
								isActive(item.href)
									? "bg-indigo-500/15 text-white"
								: "text-slate-300 hover:bg-white/5 hover:text-white"
							}`}
						>
							<span className="text-base">{item.icon}</span>
							{item.label}
						</Link>
					))}
				</nav>

				<div className="border-t border-white/10 p-3">
					<div className="truncate px-2 text-sm font-medium">{user.full_name}</div>
					<div className="truncate px-2 text-xs text-slate-400">{user.email}</div>
					<button
						onClick={handleLogout}
						className="mt-3 w-full rounded-lg border border-white/15 px-3 py-2 text-sm transition hover:bg-white/5"
					>
						Logout
					</button>
				</div>
			</aside>

			{/* Main column */}
			<div className="flex flex-1 flex-col">
				<header className="flex items-center justify-between border-b border-white/10 px-8 py-4">
					<h1 className="text-lg font-semibold capitalize">{user.role} dashboard</h1>
					<span className="rounded-full border border-white/15 bg-white/5 px-3 py-1 text-xs capitalize text-slate-300">
						{user.role}
					</span>
				</header>
				<main className="flex-1 px-8 py-8">{children}</main>
			</div>
		</div>
	)
}
