/**
 * Campus AI - role-aware dashboard home (Overview).
 *
 * Place this file at: src/app/dashboard/page.tsx  (replaces the old placeholder)
 *
 * Greets the signed-in user and shows quick-link cards for their role's
 * features. For admins it also shows a live KPI strip (counts of users by
 * role, departments, sections and drives). The layout already guards the
 * route and renders the sidebar.
 */

"use client"

import Link from "next/link"
import { useEffect, useState } from "react"
import { api } from "@/lib/api"
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
	"/dashboard/recruiter-candidates":
		"Shortlisted candidates, decisions and offers.",
	"/dashboard/recruiter-offers": "Offers your company has extended.",
	"/dashboard/recruiters":
		"Onboard companies, link drives and reveal candidate contacts.",
}

const ROLE_TAGLINE: Record<Role, string> = {
	student: "Build a verified profile and stay placement-ready.",
	teacher: "Verify student claims and manage your classes.",
	tpo: "Run drives and place verified, ranked candidates.",
	admin: "Set up the institute and manage users.",
	recruiter: "Review shortlisted candidates and extend offers.",
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

			{user.role === "admin" && <AdminStats />}

			{/* Internal college feeds are hidden from external recruiters. */}
			{user.role !== "recruiter" && (
				<>
					<AnnouncementsFeed />
					<UpcomingEvents />
				</>
			)}

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

/* ------------------------------- Admin KPIs ------------------------------- */

type UserLite = { id: number; role: Role }
type DepartmentLite = { id: number }
type SectionLite = { id: number }
type DriveLite = { id: number; is_open?: boolean }

type Stats = {
	users: number
	students: number
	teachers: number
	tpos: number
	admins: number
	departments: number
	sections: number
	drivesOpen: number
	drivesTotal: number
}

function AdminStats() {
	const [stats, setStats] = useState<Stats | null>(null)
	const [loading, setLoading] = useState(true)

	useEffect(() => {
		async function load() {
			setLoading(true)
			try {
				const [users, departments] = await Promise.all([
					api.get<UserLite[]>("/admin/users"),
					api.get<DepartmentLite[]>("/admin/departments"),
				])

				// Sections need a per-department fetch; tolerate partial failures.
				const sectionLists = await Promise.all(
					departments.map((d) =>
						api
							.get<SectionLite[]>(`/admin/departments/${d.id}/sections`)
							.catch(() => [] as SectionLite[]),
					),
				)
				const sections = sectionLists.reduce((sum, list) => sum + list.length, 0)

				// Drives are optional (endpoint may be empty / restricted).
				const drives = await api
					.get<DriveLite[]>("/drives")
					.catch(() => [] as DriveLite[])

				const next: Stats = {
					users: users.length,
					students: users.filter((u) => u.role === "student").length,
					teachers: users.filter((u) => u.role === "teacher").length,
					tpos: users.filter((u) => u.role === "tpo").length,
					admins: users.filter((u) => u.role === "admin").length,
					departments: departments.length,
					sections,
					drivesOpen: drives.filter((d) => d.is_open).length,
					drivesTotal: drives.length,
				}
				setStats(next)
			} catch {
				setStats(null)
			} finally {
				setLoading(false)
			}
		}
		load()
	}, [])

	if (loading) {
		return (
			<p className="mt-6 text-sm text-slate-400">Loading institute stats...</p>
		)
	}
	if (!stats) return null

	const items: { label: string; value: string; accent: string }[] = [
		{ label: "Total users", value: String(stats.users), accent: "text-white" },
		{
			label: "Students",
			value: String(stats.students),
			accent: "text-emerald-300",
		},
		{
			label: "Teachers",
			value: String(stats.teachers),
			accent: "text-indigo-300",
		},
		{ label: "TPOs", value: String(stats.tpos), accent: "text-violet-300" },
		{
			label: "Departments",
			value: String(stats.departments),
			accent: "text-amber-300",
		},
		{
			label: "Sections",
			value: String(stats.sections),
			accent: "text-sky-300",
		},
		{
			label: "Drives (open/total)",
			value: `${stats.drivesOpen}/${stats.drivesTotal}`,
			accent: "text-pink-300",
		},
	]

	return (
		<div className="mt-8 grid gap-4 grid-cols-2 sm:grid-cols-3 lg:grid-cols-7">
			{items.map((it) => (
				<div
					key={it.label}
					className="rounded-2xl border border-white/10 bg-white/5 p-4"
				>
					<div className={`text-2xl font-bold ${it.accent}`}>{it.value}</div>
					<div className="mt-1 text-xs text-slate-400">{it.label}</div>
				</div>
			))}
		</div>
	)
}


/* --------------------------- Announcements feed -------------------------- */

type FeedAudience = "all" | "student" | "teacher" | "tpo"

type FeedAnnouncement = {
	id: number
	title: string
	body: string
	audience: FeedAudience
	author_id: number | null
	created_at: string
}

const FEED_AUDIENCE_LABEL: Record<FeedAudience, string> = {
	all: "Everyone",
	student: "Students",
	teacher: "Teachers",
	tpo: "TPOs",
}

const FEED_AUDIENCE_STYLE: Record<FeedAudience, string> = {
	all: "bg-indigo-500/15 text-indigo-300",
	student: "bg-emerald-500/15 text-emerald-300",
	teacher: "bg-sky-500/15 text-sky-300",
	tpo: "bg-violet-500/15 text-violet-300",
}

function feedWhen(iso: string): string {
	const d = new Date(iso)
	if (Number.isNaN(d.getTime())) return iso
	return d.toLocaleString()
}

// Shown to every role on the Overview. The backend already returns only the
// announcements meant for the caller (audience "all" or their own role), so
// this is a simple read-only feed of the latest few.
function AnnouncementsFeed() {
	const [items, setItems] = useState<FeedAnnouncement[]>([])
	const [loading, setLoading] = useState(true)

	useEffect(() => {
		api
			.get<FeedAnnouncement[]>("/announcements")
			.then(setItems)
			.catch(() => setItems([]))
			.finally(() => setLoading(false))
	}, [])

	if (loading || items.length === 0) return null

	const top = items.slice(0, 5)

	return (
		<div className="mt-8">
			<h3 className="text-lg font-semibold">📣 Latest announcements</h3>
			<div className="mt-3 space-y-3">
				{top.map((a) => (
					<div
						key={a.id}
						className="rounded-2xl border border-white/10 bg-white/5 p-4"
					>
						<div className="flex items-center gap-2">
							<span className="font-medium">{a.title}</span>
							<span
								className={`rounded-full px-2 py-0.5 text-xs ${FEED_AUDIENCE_STYLE[a.audience]}`}
							>
								{FEED_AUDIENCE_LABEL[a.audience]}
							</span>
						</div>
						<p className="mt-1 text-xs text-slate-500">{feedWhen(a.created_at)}</p>
						<p className="mt-2 whitespace-pre-wrap text-sm text-slate-300">
							{a.body}
						</p>
					</div>
				))}
			</div>
		</div>
	)
}


/* ---------------------------- Upcoming events ---------------------------- */

type EventCategory = "holiday" | "exam" | "event" | "deadline"

type UpcomingEvent = {
	id: number
	title: string
	event_date: string
	end_date: string | null
	category: EventCategory
}

const EVENT_CATEGORY_LABEL: Record<EventCategory, string> = {
	holiday: "Holiday",
	exam: "Exam",
	event: "Event",
	deadline: "Deadline",
}

const EVENT_CATEGORY_STYLE: Record<EventCategory, string> = {
	holiday: "bg-rose-500/15 text-rose-300",
	exam: "bg-amber-500/15 text-amber-300",
	event: "bg-indigo-500/15 text-indigo-300",
	deadline: "bg-pink-500/15 text-pink-300",
}

function eventDay(iso: string): string {
	const d = new Date(`${iso}T00:00:00`)
	if (Number.isNaN(d.getTime())) return iso
	return d.toLocaleDateString(undefined, { day: "numeric", month: "short" })
}

// Shown to every role on the Overview. The backend returns only the entries
// meant for the caller; ?upcoming=true hides anything already in the past.
function UpcomingEvents() {
	const [items, setItems] = useState<UpcomingEvent[]>([])
	const [loading, setLoading] = useState(true)

	useEffect(() => {
		api
			.get<UpcomingEvent[]>("/calendar?upcoming=true")
			.then(setItems)
			.catch(() => setItems([]))
			.finally(() => setLoading(false))
	}, [])

	if (loading || items.length === 0) return null

	const top = items.slice(0, 6)

	return (
		<div className="mt-8">
			<h3 className="text-lg font-semibold">🗓️ Upcoming events</h3>
			<div className="mt-3 space-y-2">
				{top.map((ev) => (
					<div
						key={ev.id}
						className="flex items-center justify-between gap-3 rounded-xl border border-white/10 bg-white/5 px-4 py-3"
					>
						<div className="flex items-center gap-3">
							<span className="text-sm font-medium text-slate-200">
								{eventDay(ev.event_date)}
							</span>
							<span className="text-sm">{ev.title}</span>
						</div>
						<span
							className={`rounded-full px-2 py-0.5 text-xs ${EVENT_CATEGORY_STYLE[ev.category]}`}
						>
							{EVENT_CATEGORY_LABEL[ev.category]}
						</span>
					</div>
				))}
			</div>
		</div>
	)
}
