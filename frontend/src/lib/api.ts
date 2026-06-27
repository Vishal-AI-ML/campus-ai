/**
 * Campus AI - lightweight typed API client for the FastAPI backend.
 *
 * Responsibilities:
 *   - Prefix every request with the configured backend base URL.
 *   - Attach the JWT bearer token (kept in localStorage) when the user is logged in.
 *   - Parse JSON responses and surface backend error details as thrown errors.
 *   - Support form-encoded POST (needed by the OAuth2 /auth/login endpoint).
 *
 * Place this file at: src/lib/api.ts
 *
 * Example:
 *   import { api, setToken } from "@/lib/api"
 *   const token = await api.postForm<{ access_token: string }>("/auth/login", {
 *     username: email, password,
 *   })
 *   setToken(token.access_token)
 *   const me = await api.get<User>("/auth/me")
 */

// Base URL of the backend. Configured via .env.local (NEXT_PUBLIC_API_BASE_URL).
const BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

// localStorage key under which the JWT access token is stored.
const TOKEN_KEY = "campus_ai_token";

/** Persist the JWT access token (call this right after a successful login). */
export function setToken(token: string): void {
  if (typeof window !== "undefined") {
    window.localStorage.setItem(TOKEN_KEY, token);
  }
}

/** Read the stored JWT access token, or null when not logged in. */
export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

/** Remove the stored token (logout). */
export function clearToken(): void {
  if (typeof window !== "undefined") {
    window.localStorage.removeItem(TOKEN_KEY);
  }
}

/** Error thrown when the backend responds with a non-2xx status code. */
export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

type JsonBody = Record<string, unknown>;

/** Build the Authorization header from the stored token, when present. */
function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/** Parse a response, throwing ApiError (with backend "detail") on failure. */
async function parse<T>(res: Response): Promise<T> {
  // 204 No Content -> nothing to parse.
  if (res.status === 204) return undefined as T;

  const data = await res.json().catch(() => null);

  if (!res.ok) {
    // FastAPI returns human-readable errors under the "detail" key.
    const detail =
      data && typeof data === "object" && "detail" in data
        ? String((data as JsonBody).detail)
        : `Request failed (${res.status})`;
    throw new ApiError(res.status, detail);
  }

  return data as T;
}

async function request<T>(
  method: string,
  path: string,
  body?: JsonBody,
): Promise<T> {
  const headers: Record<string, string> = { ...authHeaders() };

  let payload: BodyInit | undefined;
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }

  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers,
    body: payload,
  });
  return parse<T>(res);
}

/**
 * POST form-url-encoded data. Required by FastAPI's OAuth2 login endpoint,
 * which expects `username` + `password` as form fields (not JSON).
 */
async function requestForm<T>(
  path: string,
  form: Record<string, string>,
): Promise<T> {
  const body = new URLSearchParams(form).toString();
  const res = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: {
      ...authHeaders(),
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body,
  });
  return parse<T>(res);
}

/**
 * POST multipart form-data (file uploads). The browser sets the multipart
 * boundary automatically, so we attach only the auth header.
 */
async function requestFile<T>(path: string, formData: FormData): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: { ...authHeaders() },
    body: formData,
  });
  return parse<T>(res);
}

/** GET a raw file/blob (e.g. a CSV template) with the auth header attached. */
async function requestBlob(path: string): Promise<Blob> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: "GET",
    headers: { ...authHeaders() },
  });
  if (!res.ok) {
    const data = await res.json().catch(() => null);
    const detail =
      data && typeof data === "object" && "detail" in data
        ? String((data as JsonBody).detail)
        : `Request failed (${res.status})`;
    throw new ApiError(res.status, detail);
  }
  return res.blob();
}

/** Thin verb helpers over the backend API. */
export const api = {
  get: <T>(path: string) => request<T>("GET", path),
  post: <T>(path: string, body?: JsonBody) => request<T>("POST", path, body),
  patch: <T>(path: string, body?: JsonBody) => request<T>("PATCH", path, body),
  delete: <T>(path: string) => request<T>("DELETE", path),
  postForm: <T>(path: string, form: Record<string, string>) =>
    requestForm<T>(path, form),
  postFile: <T>(path: string, formData: FormData) =>
    requestFile<T>(path, formData),
  getBlob: (path: string) => requestBlob(path),
};
