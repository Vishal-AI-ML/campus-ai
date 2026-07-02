"use client"

/**
 * Campus AI - embedded, auto-playing product tour for the marketing landing.
 *
 * Place this file at: src/components/landing/ProductTour.tsx
 *
 * Embeds the self-contained demo (public/demo/campus-ai-tour.html) in a
 * browser-chrome frame, lets visitors pick a role, and opens fullscreen.
 * All data shown inside is SAMPLE data - the demo carries its own
 * "Demo preview · sample data" flag.
 */

import { useState } from "react"

const DEMO_SRC = "/demo/campus-ai-tour.html"

type RoleOption = {
	id: string
	emoji: string
	label: string
	desc: string
}

const ROLE_OPTIONS: RoleOption[] = [
	{ id: "full", emoji: "▶️", label: "Full guided tour", desc: "Every role, end to end" },
	{ id: "student", emoji: "🎓", label: "Student", desc: "Attendance, skills, resume, drives" },
	{ id: "teacher", emoji: "👩‍🏫", label: "Teacher", desc: "Face attendance, verify, analytics" },
	{ id: "tpo", emoji: "🏢", label: "Placement Cell", desc: "Drives, eligibility, applicants" },
	{ id: "recruiter", emoji: "🤝", label: "Recruiter", desc: "Verified candidates, offers" },
	{ id: "admin", emoji: "🛠️", label: "Admin", desc: "Institute, users, audit log" },
]

export default function ProductTour() {
	const [role, setRole] = useState<string>("full")
	const [fullscreen, setFullscreen] = useState<boolean>(false)
	const src = `${DEMO_SRC}?tour=${role}&theme=light`

	return (
		<section id="demo" className="mx-auto max-w-6xl scroll-mt-20 px-6 py-16">
			<div className="text-center">
				<p className="text-sm font-semibold uppercase tracking-wide text-indigo-500">
					See it live
				</p>
				<h2 className="mt-2 text-3xl font-bold">Watch the product tour</h2>
				<p className="mx-auto mt-3 max-w-2xl text-slate-500">
					An auto-playing walkthrough of every role. No login needed — all data
					shown is sample data, not a real account.
				</p>
			</div>

			{/* Role chooser */}
			<div className="mt-8 flex flex-wrap justify-center gap-2">
				{ROLE_OPTIONS.map((option) => (
					<button
						key={option.id}
						type="button"
						onClick={() => setRole(option.id)}
						title={option.desc}
						className={
							"rounded-full border px-4 py-2 text-sm font-medium transition " +
							(role === option.id
								? "border-indigo-500 bg-indigo-500 text-white"
								: "border-slate-300 bg-white text-slate-600 hover:border-indigo-300 hover:text-indigo-600")
						}
					>
						<span className="mr-1.5">{option.emoji}</span>
						{option.label}
					</button>
				))}
			</div>

			{/* Browser-chrome frame */}
			<div className="mx-auto mt-8 max-w-4xl rounded-2xl border border-slate-200 bg-white p-2 shadow-xl">
				<div className="overflow-hidden rounded-xl border border-slate-200">
					<div className="flex items-center gap-1.5 border-b border-slate-200 bg-slate-100 px-4 py-2.5">
						<span className="h-3 w-3 rounded-full bg-rose-400" />
						<span className="h-3 w-3 rounded-full bg-amber-400" />
						<span className="h-3 w-3 rounded-full bg-emerald-400" />
						<span className="ml-3 flex items-center gap-1.5 text-xs text-slate-500">
							<span className="inline-block h-2 w-2 animate-pulse rounded-full bg-emerald-400" />
							Campus AI · demo · sample data
						</span>
						<button
							type="button"
							onClick={() => setFullscreen(true)}
							className="ml-auto text-xs font-medium text-indigo-600 hover:text-indigo-500"
						>
							Open fullscreen
						</button>
					</div>
					<iframe
						key={src}
						src={src}
						title="Campus AI product tour"
						className="block h-[460px] w-full bg-white"
					/>
				</div>
			</div>
			<p className="mt-4 text-center text-xs text-slate-500">
				Live, auto-playing preview — sample data, not a real account.
			</p>

			{/* Fullscreen modal */}
			{fullscreen ? (
				<div className="fixed inset-0 z-50 flex flex-col bg-white/90 p-3 backdrop-blur">
					<div className="flex items-center justify-between px-2 py-2 text-white">
						<span className="text-sm font-semibold">
							Campus AI · product tour · sample data
						</span>
						<button
							type="button"
							onClick={() => setFullscreen(false)}
							className="rounded-full border border-white/30 px-4 py-1.5 text-sm text-white transition hover:bg-slate-100"
						>
							Close ✕
						</button>
					</div>
					<iframe
						key={`fs-${src}`}
						src={src}
						title="Campus AI product tour fullscreen"
						className="min-h-0 w-full flex-1 rounded-xl bg-white"
					/>
				</div>
			) : null}
		</section>
	)
}
