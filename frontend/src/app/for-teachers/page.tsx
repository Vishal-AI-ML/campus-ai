/**
 * Campus AI - /for-teachers route.
 * Place this file at: src/app/for-teachers/page.tsx
 */

import RoleLanding, { roleMetadata } from "@/components/RoleLanding"

export const metadata = roleMetadata("teachers")

export default function ForTeachersPage() {
	return <RoleLanding slug="teachers" />
}
