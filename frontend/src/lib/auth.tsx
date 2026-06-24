/**
 * Campus AI - client-side auth context + role helpers.
 *
 * Place this file at: src/lib/auth.tsx
 *
 * Provides:
 *   - <AuthProvider>: loads the current user once (via /auth/me) and guards the
 *     route (redirects to /login when there is no valid session).
 *   - useCurrentUser(): read the loaded user + loading state from any client
 *     component inside the provider.
 *   - NAV_BY_ROLE: the sidebar navigation items shown for each role (only
 *     features whose backend already exists are listed).
 */

"use client"

import { createContext, useContext, useEffect, useState, type ReactNode } from "react"
import { useRouter } from "next/navigation"
import { api, clearToken, getToken, ApiError } from "@/lib/api"

export type Role = "student" | "teacher" | "tpo" | "admin"

export type CurrentUser = {
	id: number
	email: string
	full_name: string
	role: Role
	is_active: boolean
}

type AuthState = { user: CurrentUser | null; loading: boolean }

const AuthContext = createContext<AuthState>({ user: null, loading: true })

/** Loads the signed-in user once and shares it with the whole dashboard tree. */
export function AuthProvider({ children }: { children: ReactNode }) {
	const router = useRouter()
	const [user, setUser] = useState<CurrentUser | null>(null)
	const [loading, setLoading] = useState(true)

	useEffect(() => {
		// No token -> not signed in.
		if (!getToken()) {
			router.replace("/login")
			return
		}

		api
			.get<CurrentUser>("/auth/me")
			.then(setUser)
			.catch((err) => {
				// Expired/invalid token -> clear and bounce to login.
				if (err instanceof ApiError && err.status === 401) clearToken()
				router.replace("/login")
			})
			.finally(() => setLoading(false))
	}, [router])

	const value: AuthState = { user, loading }
	return (
		<AuthContext.Provider value={value}>
			{children}
		</AuthContext.Provider>
	)
}

/** Read the current user + loading flag from within <AuthProvider>. */
export function useCurrentUser(): AuthState {
	return useContext(AuthContext)
}

export type NavItem = { label: string; href: string; icon: string }

/**
 * Sidebar items per role. Only features with a working backend are listed;
 * more are added as their pages get built.
 */
export const NAV_BY_ROLE: Record<Role, NavItem[]> = {
	student: [
		{ label: "Overview", href: "/dashboard", icon: "\u{1F3E0}" },
		{ label: "Attendance", href: "/dashboard/attendance", icon: "\u{1F5D3}\uFE0F" },
		{ label: "Academics", href: "/dashboard/academics", icon: "\u{1F4CA}" },
		{ label: "Skills", href: "/dashboard/skills", icon: "\u{1F6E1}\uFE0F" },
		{ label: "Projects", href: "/dashboard/projects", icon: "\u{1F9E9}" },
		{ label: "AI Mentor", href: "/dashboard/mentor", icon: "\u{1F916}" },
	],
	teacher: [
		{ label: "Overview", href: "/dashboard", icon: "\u{1F3E0}" },
		{ label: "Verify Queue", href: "/dashboard/verify", icon: "\u2705" },
		{ label: "Attendance", href: "/dashboard/attendance", icon: "\u{1F5D3}\uFE0F" },
		{ label: "Gradebook", href: "/dashboard/gradebook", icon: "\u{1F4D2}" },
	],
	tpo: [
		{ label: "Overview", href: "/dashboard", icon: "\u{1F3E0}" },
		{ label: "Drives", href: "/dashboard/drives", icon: "\u{1F3E2}" },
		{ label: "Applications", href: "/dashboard/applications", icon: "\u{1F4E8}" },
	],
	admin: [
		{ label: "Overview", href: "/dashboard", icon: "\u{1F3E0}" },
		{ label: "Users", href: "/dashboard/users", icon: "\u{1F465}" },
		{ label: "Departments", href: "/dashboard/departments", icon: "\u{1F3EB}" },
	],
}
