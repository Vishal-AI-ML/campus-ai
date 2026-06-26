/**
 * Campus AI - /for-tpos route.
 * Place this file at: src/app/for-tpos/page.tsx
 */

import RoleLanding, { roleMetadata } from "@/components/RoleLanding"

export const metadata = roleMetadata("tpos")

export default function ForTposPage() {
	return <RoleLanding slug="tpos" />
}
