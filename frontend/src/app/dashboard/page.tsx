/**
 * Campus AI - role-aware dashboard home (Overview).
 *
 * Place this file at: src/app/dashboard/page.tsx  (replaces the old placeholder)
 *
 * Greets the signed-in user and shows quick-link cards for their role's
 * features. The layout already guards the route and renders the sidebar.
 */

"use client"

import Link from "next/link"
import { useCurrentUser, NAV_BY_ROLE, type Role } from "@/lib/auth"

// Short blurb per quick-link, keyed by destination href.
const BLURBS: Record<string, string> = {
	"/dashboard/attendance": "Your attendance record and percentage.",
	"/dashboard/academics": "Results, CGPA and per-semester SGPA.",
	"/dashboard/skills": "Claim skills with proof and track verification.",
	"/dashboard/projects": "Your projects and verified contributions.",
	"/dashboard/mentor": "Ask the AI mentor, grounded on your verified profile.",
	"/dashboard/verify": "Review and verify student skill & project claims.",
	"/dashboard/gradebook": "Manage subjects and enter student marks.",
	"/dashboard/drives": "Post placement drives and check eligibility.",
	"/dashboard/applications": "Review applicants and shortlist candidates.",
	"/dashboard/users": "Manage user accounts, roles and access.",
	"/dashboard/departments": "Manage departments and sections.",
}

const ROLE_TAGLINE: Record<Role, string> = {
	student: "Build a verified profile and stay placement-ready.",
	teacher: "Verify student claims and manage your classes.",
	tpo: "Run drives and place verified, ranked candidates.",
	admin: "Set up the institute and manage users.",
}

export default function DashboardHome() {
	const { user } = useCurrentUser()
	if (!user) return null

	// All role links except the Overview card itself.
	const cards = (NAV_BY_ROLE[user.role] ?? []).filter(
		(item) => item.href !== "/dashboard",
	)

	return (
		<div>
			<h2 className="text-3xl font-bold">Welcome, {user.full_name}</h2>
			<p className="mt-2 text-slate-400">{ROLE_TAGLINE[user.role]}</p>

			<div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
				{cards.map((item) => (
					<Link
						key={item.href}
						href={item.href}
						className="rounded-2xl border border-white/10 bg-white/5 p-5 transition hover:border-white/20 hover:bg-white/[0.07]"
					>
						<div className="text-2xl">{item.icon}</div>
						<div className="mt-3 text-lg font-semibold">{item.label}</div>
						<p className="mt-1 text-sm text-slate-400">
							{BLURBS[item.href] ?? ""}
						</p>
					</Link>
				))}
			</div>
		</div>
	)
}
