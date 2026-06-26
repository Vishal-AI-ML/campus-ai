/**
 * Campus AI - shared marketing/site content (single source of truth).
 *
 * Place this file at: src/lib/marketing.ts
 *
 * Every marketing surface (home, /features/[slug], /for-[role], footer) reads
 * from here, so content stays consistent and is edited in one place.
 */

export type Feature = {
	/** URL slug, e.g. "verified-skills" -> /features/verified-skills */
	slug: string
	icon: string
	title: string
	tagline: string
	description: string
	highlights: string[]
}

export const FEATURES: Feature[] = [
	{
		slug: "face-attendance",
		icon: "📸",
		title: "Face Attendance",
		tagline: "From the first check-in.",
		description:
			"Snap one class photo and AI matches every face against your enrolled roster — the teacher just confirms with one tap.",
		highlights: [
			"AI face matching against the enrolled roster",
			"One-tap, human-in-the-loop confirmation",
			"No more proxy attendance",
			"Automatic attendance % per student",
		],
	},
	{
		slug: "verified-skills",
		icon: "🛡️",
		title: "Verified Skills",
		tagline: "Proof, not claims.",
		description:
			"Students claim skills with evidence. AI scores the proof and a mentor verifies — only verified skills ever reach resumes and recruiters.",
		highlights: [
			"Evidence-backed skill claims",
			"AI advisory score on every proof",
			"Mentor verify / flag decision",
			"Only verified data counts",
		],
	},
	{
		slug: "verified-projects",
		icon: "🧩",
		title: "Verified Projects",
		tagline: "Credit where it is due.",
		description:
			"Group projects are verified per contributor, so a freeloader never gets credit and the real builders stand out.",
		highlights: [
			"Per-member contribution review",
			"AI scoring for each contributor",
			"Mentor verifies individually",
			"Fair, fraud-resistant credit",
		],
	},
	{
		slug: "ai-resume",
		icon: "📄",
		title: "AI Resume + ATS",
		tagline: "Resumes that pass the bots.",
		description:
			"Turn verified skills and projects into a polished resume, then score it against any job description's ATS keywords.",
		highlights: [
			"Built only from verified data",
			"ATS keyword-match scoring",
			"Multiple resume versions",
			"Recruiter-ready output",
		],
	},
	{
		slug: "ai-mentor",
		icon: "🤖",
		title: "AI Career Mentor",
		tagline: "Guidance grounded in your profile.",
		description:
			"A career mentor that reasons over the student's verified profile and a curated knowledge base — grounded and cited, never hallucinated.",
		highlights: [
			"RAG over the verified profile",
			"Curated career knowledge base",
			"Grounded, cited answers",
			"Available 24/7",
		],
	},
	{
		slug: "academics",
		icon: "📊",
		title: "Academics & Results",
		tagline: "Always-current CGPA.",
		description:
			"Credit-weighted SGPA and CGPA are computed automatically from results, semester by semester.",
		highlights: [
			"Automatic SGPA / CGPA",
			"Semester-wise breakdown",
			"Credit-weighted accuracy",
			"Feeds placement eligibility",
		],
	},
	{
		slug: "placement-drives",
		icon: "🏢",
		title: "Placement Drives",
		tagline: "...to the final offer letter.",
		description:
			"TPOs create drives with criteria; an explainable eligibility engine filters and ranks candidates on verified data.",
		highlights: [
			"Criteria-based drive builder",
			"Explainable eligibility engine",
			"Ranked, verified candidates",
			"End-to-end application tracking",
		],
	},
	{
		slug: "analytics",
		icon: "📈",
		title: "Analytics & At-risk",
		tagline: "See trouble early.",
		description:
			"Class and institute dashboards surface attendance, performance and at-risk students before it is too late.",
		highlights: [
			"Class & institute KPIs",
			"At-risk early warning",
			"Placement analytics",
			"Data-driven decisions",
		],
	},
	{
		slug: "admin-rbac",
		icon: "🛠️",
		title: "Admin & RBAC",
		tagline: "Your institute, structured.",
		description:
			"Departments, sections, subjects, users and roles — multi-tenant and access-controlled from day one.",
		highlights: [
			"Departments / sections / subjects",
			"Role-based access control",
			"Bulk user import",
			"Multi-tenant ready",
		],
	},
]

export function getFeature(slug: string): Feature | undefined {
	return FEATURES.find((f) => f.slug === slug)
}

export type RolePage = {
	/** "students" -> route /for-students */
	slug: string
	emoji: string
	title: string
	pitch: string
	points: string[]
}

export const ROLES: RolePage[] = [
	{
		slug: "students",
		emoji: "👨\u200d🎓",
		title: "For Students",
		pitch: "Build a verified profile that actually gets you placed.",
		points: [
			"Claim skills & projects with proof",
			"Track attendance and CGPA",
			"Generate an ATS-ready resume",
			"Apply to drives you are eligible for",
			"Get 24/7 AI career guidance",
		],
	},
	{
		slug: "teachers",
		emoji: "👩\u200d🏫",
		title: "For Teachers",
		pitch: "Less busywork, more teaching.",
		points: [
			"Face attendance in one tap",
			"Verify skills & projects from a queue",
			"Gradebook and class analytics",
			"Spot at-risk students early",
		],
	},
	{
		slug: "tpos",
		emoji: "🏢",
		title: "For TPOs",
		pitch: "Place verified, ranked candidates faster.",
		points: [
			"Create drives with custom criteria",
			"Auto-filter by verified eligibility",
			"Ranked candidate shortlists",
			"Track every application",
			"Recruiter-ready data",
		],
	},
	{
		slug: "admins",
		emoji: "🛠️",
		title: "For Admins",
		pitch: "Run the whole institute from one console.",
		points: [
			"Set up departments & sections",
			"Manage users and roles",
			"Academic calendar & announcements",
			"Audit log & governance",
			"Multi-tenant control",
		],
	},
]

export function getRole(slug: string): RolePage | undefined {
	return ROLES.find((r) => r.slug === slug)
}

export type NavLink = { label: string; href: string }

export const MARKETING_NAV: NavLink[] = [
	{ label: "Features", href: "/#features" },
	{ label: "Pricing", href: "/pricing" },
	{ label: "Contact", href: "/contact" },
]
