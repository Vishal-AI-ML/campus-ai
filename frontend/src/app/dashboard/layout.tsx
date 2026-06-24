/**
 * Campus AI - layout for all /dashboard/* routes.
 *
 * Place this file at: src/app/dashboard/layout.tsx
 *
 * Wraps every dashboard page in the auth provider (loads the user / guards the
 * route) and the shared app shell (sidebar + topbar).
 */

import { AuthProvider } from "@/lib/auth"
import AppShell from "@/components/AppShell"

export default function DashboardLayout({
	children,
}: {
	children: React.ReactNode
}) {
	return (
		<AuthProvider>
			<AppShell>{children}</AppShell>
		</AuthProvider>
	)
}
