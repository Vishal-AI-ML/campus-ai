/**
 * Campus AI - login page (client component).
 *
 * Place this file at: src/app/login/page.tsx
 *
 * Posts credentials to the backend's OAuth2 /auth/login endpoint (form-encoded,
 * `username` = email), stores the returned JWT, and redirects to /dashboard.
 */

"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { api, setToken, ApiError } from "@/lib/api"

type LoginResponse = { access_token: string; token_type: string }

export default function LoginPage() {
	const router = useRouter()
	const [email, setEmail] = useState("")
	const [password, setPassword] = useState("")
	const [error, setError] = useState<string | null>(null)
	const [loading, setLoading] = useState(false)

	async function handleSubmit(e: React.FormEvent) {
		e.preventDefault()
		setError(null)
		setLoading(true)
		try {
			// OAuth2PasswordRequestForm expects the email under `username`.
			const res = await api.postForm<LoginResponse>("/auth/login", {
				username: email,
				password,
			})
			setToken(res.access_token)
			router.push("/dashboard")
		} catch (err) {
			setError(
				err instanceof ApiError
					? err.message
					: "Could not reach the server. Is the backend running?",
			)
		} finally {
			setLoading(false)
		}
	}

	return (
		<div className="flex min-h-screen items-center justify-center bg-slate-950 px-6 text-slate-100">
			<div className="w-full max-w-sm">
				<Link href="/" className="mb-8 flex items-center justify-center gap-2 font-semibold">
					<span className="grid h-9 w-9 place-items-center rounded-lg bg-gradient-to-br from-indigo-500 to-violet-500 text-sm font-bold">
						C
					</span>
					<span className="text-xl">Campus AI</span>
				</Link>

				<div className="rounded-2xl border border-white/10 bg-white/5 p-8">
					<h1 className="text-2xl font-bold">Welcome back</h1>
					<p className="mt-1 text-sm text-slate-400">
						Sign in to your Campus AI account.
					</p>

					<form onSubmit={handleSubmit} className="mt-6 space-y-4">
						<div>
							<label htmlFor="email" className="block text-sm font-medium text-slate-300">
								Email
							</label>
							<input
								id="email"
								type="email"
								autoComplete="email"
								required
								value={email}
								onChange={(e) => setEmail(e.target.value)}
								className="mt-1 w-full rounded-lg border border-white/10 bg-slate-900 px-3 py-2 text-sm outline-none focus:border-indigo-400"
								placeholder="you@campus.ai"
							/>
						</div>

						<div>
							<label htmlFor="password" className="block text-sm font-medium text-slate-300">
								Password
							</label>
							<input
								id="password"
								type="password"
								autoComplete="current-password"
								required
								value={password}
								onChange={(e) => setPassword(e.target.value)}
								className="mt-1 w-full rounded-lg border border-white/10 bg-slate-900 px-3 py-2 text-sm outline-none focus:border-indigo-400"
								placeholder="\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022"
							/>
						</div>

						{error && (
							<p className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">
								{error}
							</p>
						)}

						<button
							type="submit"
							disabled={loading}
							className="w-full rounded-lg bg-gradient-to-r from-indigo-500 to-violet-500 px-4 py-2.5 font-medium text-white transition hover:opacity-90 disabled:opacity-50"
						>
							{loading ? "Signing in..." : "Sign in"}
						</button>
					</form>
				</div>

				<p className="mt-6 text-center text-sm text-slate-500">
					<Link href="/" className="hover:text-slate-300">
						\u2190 Back to home
					</Link>
				</p>
			</div>
		</div>
	)
}
