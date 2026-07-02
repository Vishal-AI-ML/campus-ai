/**
 * Campus AI - reusable file upload widget + stored-file link.
 *
 * Place this file at: src/components/FileUpload.tsx
 *
 * <FileUpload> lets a user pick a file, uploads it directly to Supabase
 * Storage via a signed URL, and calls onUploaded(path) with the stored object
 * path (which the parent saves into the entity's *_url field).
 *
 * <StoredFileLink> renders a link/button for a saved *_url value: external
 * http(s) links open directly; private stored paths are signed on click.
 */

"use client"

import { useState, type ReactNode } from "react"
import { ApiError } from "@/lib/api"
import {
	getDownloadUrl,
	isStoredPath,
	uploadFile,
	type UploadKind,
} from "@/lib/uploadsApi"

type FileUploadProps = {
	kind: UploadKind
	onUploaded: (path: string) => void
	/** Comma-separated accept filter, e.g. ".pdf,.jpg,.png". */
	accept?: string
	label?: string
	disabled?: boolean
}

export default function FileUpload({
	kind,
	onUploaded,
	accept,
	label = "Upload file",
	disabled,
}: FileUploadProps) {
	const [busy, setBusy] = useState(false)
	const [error, setError] = useState<string | null>(null)
	const [uploaded, setUploaded] = useState<string | null>(null)

	async function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
		const file = e.target.files?.[0]
		// Reset the input so picking the same file again re-fires onChange.
		e.target.value = ""
		if (!file) return

		setBusy(true)
		setError(null)
		try {
			const path = await uploadFile(file, kind)
			setUploaded(file.name)
			onUploaded(path)
		} catch (err) {
			const msg =
				err instanceof ApiError
					? err.status === 503
						? "File uploads are not enabled yet."
						: err.message
					: err instanceof Error
						? err.message
						: "Upload failed."
			setError(msg)
		} finally {
			setBusy(false)
		}
	}

	return (
		<div>
			<label
				className={`inline-flex cursor-pointer items-center gap-2 rounded-lg border border-white/15 bg-slate-900 px-3 py-2 text-sm transition hover:bg-white/5 ${
					disabled || busy ? "cursor-not-allowed opacity-50" : ""
				}`}
			>
				<span>{busy ? "Uploading..." : label}</span>
				<input
					type="file"
					accept={accept}
					disabled={disabled || busy}
					onChange={handleChange}
					className="hidden"
				/>
			</label>
			{uploaded && !error && (
				<span className="ml-2 text-xs text-emerald-300">
					Attached: {uploaded}
				</span>
			)}
			{error && <p className="mt-1 text-xs text-red-300">{error}</p>}
		</div>
	)
}

type StoredFileLinkProps = {
	value: string
	className?: string
	children?: ReactNode
}

/** Opens a saved *_url value: external links directly, stored paths via a signed URL. */
export function StoredFileLink({
	value,
	className,
	children,
}: StoredFileLinkProps) {
	const [busy, setBusy] = useState(false)
	const [error, setError] = useState<string | null>(null)

	if (!isStoredPath(value)) {
		return (
			<a href={value} target="_blank" rel="noreferrer" className={className}>
				{children ?? value}
			</a>
		)
	}

	async function open() {
		setBusy(true)
		setError(null)
		try {
			const url = await getDownloadUrl(value)
			window.open(url, "_blank", "noopener")
		} catch {
			setError("Could not open file.")
		} finally {
			setBusy(false)
		}
	}

	return (
		<>
			<button
				type="button"
				onClick={open}
				disabled={busy}
				className={className}
			>
				{busy ? "Opening..." : (children ?? "View file")}
			</button>
			{error && <span className="ml-2 text-xs text-red-300">{error}</span>}
		</>
	)
}
