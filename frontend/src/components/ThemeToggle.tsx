"use client"

import { useEffect, useState } from "react"

export default function ThemeToggle({ className = "" }: { className?: string }) {
	const [theme, setTheme] = useState<"light" | "dark">("light")
	const [mounted, setMounted] = useState(false)

	useEffect(() => {
		setMounted(true)
		const stored =
			typeof window !== "undefined" ? localStorage.getItem("campus-theme") : null
		const isDark =
			stored === "dark" ||
			(typeof document !== "undefined" &&
				document.documentElement.classList.contains("dark"))
		setTheme(isDark ? "dark" : "light")
	}, [])

	function toggle() {
		const next = theme === "dark" ? "light" : "dark"
		setTheme(next)
		document.documentElement.classList.toggle("dark", next === "dark")
		try {
			localStorage.setItem("campus-theme", next)
		} catch {}
	}

	return (
		<button
			type="button"
			onClick={toggle}
			aria-label="Toggle dark mode"
			title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
			className={`grid h-9 w-9 place-items-center rounded-lg border border-slate-200 bg-white text-base transition hover:bg-slate-100 dark:border-white/15 dark:bg-slate-900 dark:hover:bg-white/10 ${className}`}
		>
			{mounted && theme === "dark" ? "\u2600\ufe0f" : "\ud83c\udf19"}
		</button>
	)
}
