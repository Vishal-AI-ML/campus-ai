/**
 * Campus AI - /for-admins route.
 * Place this file at: src/app/for-admins/page.tsx
 */

import RoleLanding, { roleMetadata } from "@/components/RoleLanding"

export const metadata = roleMetadata("admins")

export default function ForAdminsPage() {
	return <RoleLanding slug="admins" />
}
