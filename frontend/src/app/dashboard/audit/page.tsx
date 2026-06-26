/**
 * Campus AI - Admin: Audit Log (governance trail).
 *
 * Place this file at: src/app/dashboard/audit/page.tsx
 *
 * Read-only, newest-first timeline of sensitive admin actions (who did what,
 * when). Admin-only - the backend rejects other roles with 403, and this page
 * also shows a soft guard. Supports filtering by action key.
 *
 * Backend endpoint:
 *   GET /audit?action={key}&limit={n}
 *     -> [{ id, actor_id, actor_email, action, target_type, target_id, summary, created_at }]
 */

"use client"

import { useEffect, useState } from "react"
import { api, ApiError } from "@/lib/api"
import { useCurrentUser } from "@/lib/auth"

type AuditLog = {
	id: number
	actor_id: number | null
	actor_email: string | null
	action: string
	target_type: string | null
	target_id: string | null
	summary: string
	created_at: string
}

// Known action keys -> friendly label + badge colour. Unknown keys fall back
// to the raw key with a neutral style, so new server actions still render.
const ACTION_META: Record<string, { label: string; style: string }> = {
	"user.create": { label: "User created", style: "bg-emerald-500/15 text-emerald-300" },
	"user.role_change": { label: "Role changed", style: "bg-indigo-500/15 text-indigo-300" },
	"user.status_change": { label: "Status changed", style: "bg-amber-500/15 text-amber-300" },
	"user.section_assign": { label: "Section assigned", style: "bg-sky-500/15 text-sky-300" },
	"department.create": { label: "Department created", style: "bg-violet-500/15 text-violet-300" },
	"section.create": { label: "Section created", style: "bg-violet-500/15 text-violet-300" },
}

function actionMeta(action: string): { label: string; style: string } {
	return (
		ACTION_META[action] ?? {
			label: action,
			style: "bg-white/10 text-slate-300",
		}
	)
}

const FILTERS: { value: string; label: string }[] = [
	{ value: "", label: "All actions" },
	{ value: "user.create", label: "User created" },
	{ value: "user.role_change", label: "Role changed" },
	{ value: "user.status_change", label: "Status changed" },
	{ value: "user.section_assign", label: "Section assigned" },
	{ value: "department.create", label: "Department created" },
	{ value: "section.create", label: "Section created" },
]

const inputClass =
	"rounded-lg border border-white/10 bg-slate-900 px-3 py-2 text-sm outline-none focus:border-indigo-400"

function formatWhen(iso: string): string {
	const d = new Date(iso)
	if (Number.isNaN(d.getTime())) return iso
	return d.toLocaleString(undefined, {
		day: "numeric",
		month: "short",
		year: "numeric",
		hour: "2-digit",
		minute: "2-digit",
	})
}

export default function AuditLogPage() {
	const { user } = useCurrentUser()

	const [items, setItems] = useState<AuditLog[]>([])
	const [loading, setLoading] = useState(true)
	const [error, setError] = useState<string | null>(null)
	const [filter, setFilter] = useState("")

	async function load(action: string) {
		setLoading(true)
		setError(null)
		try {
			const qs = action ? `?action=${encodeURIComponent(action)}` : ""
			setItems(await api.get<AuditLog[]>(`/audit${qs}`))
		} catch (err) {
			setError(
				err instanceof ApiError ? err.message : "Could not load the audit log.",
			)
		} finally {
			setLoading(false)
		}
	}

	useEffect(() => {
		load(filter)
	}, [filter])

	if (user && user.role !== "admin") {
		return (
			<div>
				<h2 className="text-2xl font-bold">Audit Log</h2>
				<p className="mt-2 text-slate-400">
					The audit log is available to admins only.
				</p>
			</div>
		)
	}

	return (
		<div>
			<div className="flex flex-wrap items-center justify-between gap-3">
				<div>
					<h2 className="text-2xl font-bold">Audit Log</h2>
					<p className="mt-1 text-sm text-slate-400">
						Append-only trail of governance actions, newest first.
					</p>
				</div>
				<select
					value={filter}
					onChange={(e) => setFilter(e.target.value)}
					className={inputClass}
				>
					{FILTERS.map((f) => (
						<option key={f.value} value={f.value}>
							{f.label}
						</option>
					))}
				</select>
			</div>

			{error && (
				<p className="mt-4 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">
					{error}
				</p>
			)}

			{loading ? (
				<p className="mt-6 text-slate-400">Loading...</p>
			) : items.length === 0 ? (
				<p className="mt-6 text-slate-400">No audit entries yet.</p>
			) : (
				<div className="mt-6 space-y-3">
					{items.map((entry) => {
						const meta = actionMeta(entry.action)
						return (
							<div
								key={entry.id}
								className="rounded-2xl border border-white/10 bg-white/5 p-5"
							>
								<div className="flex flex-wrap items-center gap-2">
									<span
										className={`rounded-full px-2 py-0.5 text-xs ${meta.style}`}
									>
										{meta.label}
									</span>
									<span className="text-xs text-slate-500">
										{formatWhen(entry.created_at)}
									</span>
								</div>
								<p className="mt-2 text-sm text-slate-200">{entry.summary}</p>
								<p className="mt-1 text-xs text-slate-500">
									by {entry.actor_email ?? "(deleted user)"}
									{entry.target_type
										? ` \u2022 ${entry.target_type}${entry.target_id ? ` #${entry.target_id}` : ""}`
										: ""}
								</p>
							</div>
						)
					})}
				</div>
			)}
		</div>
	)
}
