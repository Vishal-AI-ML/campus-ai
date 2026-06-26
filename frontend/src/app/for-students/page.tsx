/**
 * Campus AI - /for-students route.
 * Place this file at: src/app/for-students/page.tsx
 */

import RoleLanding, { roleMetadata } from "@/components/RoleLanding"

export const metadata = roleMetadata("students")

export default function ForStudentsPage() {
	return <RoleLanding slug="students" />
}
