/**
 * Campus AI - client helpers for Supabase Storage signed-URL uploads.
 *
 * Place this file at: src/lib/uploadsApi.ts
 *
 * Flow (the file bytes never touch our API server):
 *   1. ask the backend to sign an upload URL  -> POST /files/sign-upload
 *   2. PUT the file straight to Supabase Storage at that URL
 *   3. keep the returned object `path` (store it in the entity's *_url column)
 *   4. to view later, mint a short-lived signed download URL on demand
 *      -> POST /files/sign-download
 *
 * When storage is not configured on the backend the sign endpoints return 503,
 * which surfaces here as an ApiError the caller can show to the user.
 */

import { api } from "@/lib/api"

/** Upload categories the backend allows (must match files.py ALLOWED_EXTENSIONS). */
export type UploadKind = "certificate" | "proof" | "resume" | "material"

type SignUploadResponse = { path: string; upload_url: string; token: string }
type SignDownloadResponse = { download_url: string; expires_in: number }

/**
 * Upload a single file and return the stored object path.
 * Throws (ApiError from the sign step, or Error on the storage PUT) on failure.
 */
export async function uploadFile(file: File, kind: UploadKind): Promise<string> {
	const signed = await api.post<SignUploadResponse>("/files/sign-upload", {
		filename: file.name,
		kind,
	})

	// PUT the raw bytes straight to Supabase Storage (absolute signed URL,
	// token is already in the query string - no auth header needed here).
	const res = await fetch(signed.upload_url, {
		method: "PUT",
		headers: { "Content-Type": file.type || "application/octet-stream" },
		body: file,
	})
	if (!res.ok) {
		throw new Error(`Upload failed (${res.status}). Please try again.`)
	}
	return signed.path
}

/** Mint a short-lived signed URL to view/download a stored object path. */
export async function getDownloadUrl(path: string): Promise<string> {
	const res = await api.post<SignDownloadResponse>("/files/sign-download", {
		path,
	})
	return res.download_url
}

/**
 * Heuristic used across the UI: an external link starts with http(s):// and is
 * opened directly; anything else is treated as a private stored object path
 * that must be signed before it can be opened.
 */
export function isStoredPath(value: string): boolean {
	return value.length > 0 && !/^https?:\/\//i.test(value)
}
