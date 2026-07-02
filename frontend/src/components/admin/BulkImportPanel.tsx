/**
 * Campus AI - Admin: Bulk user import (CSV).
 *
 * Place this file at: src/components/admin/BulkImportPanel.tsx
 *
 * Lets an admin upload a CSV to create many accounts at once. Shows a per-row
 * result (created / skipped + reason) and any auto-generated temporary
 * passwords so they can be shared once.
 *
 * Backend endpoints:
 *   GET  /admin/users/bulk-template  -> sample CSV download
 *   POST /admin/users/bulk-import    -> multipart "file"; returns a summary
 */

"use client";

import { useRef, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { Role } from "@/lib/auth";

type RowResult = {
  row: number;
  email: string | null;
  status: "created" | "skipped";
  detail: string;
  user_id: number | null;
  role: Role | null;
  temp_password: string | null;
};

type ImportResult = {
  total_rows: number;
  created: number;
  skipped: number;
  results: RowResult[];
};

export function BulkImportPanel({ onImported }: { onImported?: () => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  async function downloadTemplate() {
    setError(null);
    try {
      const blob = await api.getBlob("/admin/users/bulk-template");
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "campus_users_template.csv";
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(
        e instanceof ApiError ? e.message : "Could not download template.",
      );
    }
  }

  async function runImport() {
    if (!file) {
      setError("Choose a CSV file first.");
      return;
    }
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const res = await api.postFile<ImportResult>(
        "/admin/users/bulk-import",
        fd,
      );
      setResult(res);
      if (res.created > 0) onImported?.();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Import failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-900 p-6">
      <h3 className="text-lg font-semibold">Bulk import (CSV)</h3>
      <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
        Create many accounts at once. Columns:{" "}
        <code className="text-slate-600 dark:text-slate-300">
          full_name, email, role, password, section_id
        </code>
        . Role defaults to <code className="text-slate-600 dark:text-slate-300">student</code>;
        blank passwords are auto-generated and shown once below.
      </p>

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <button
          onClick={downloadTemplate}
          className="rounded-lg border border-slate-300 dark:border-white/15 px-3 py-2 text-sm text-slate-700 dark:text-slate-200 transition hover:bg-slate-100 dark:hover:bg-white/10"
        >
          Download template
        </button>
        <input
          ref={inputRef}
          type="file"
          accept=".csv,text/csv"
          onChange={(e) => {
            setFile(e.target.files?.[0] ?? null);
            setResult(null);
          }}
          className="text-sm text-slate-600 dark:text-slate-300 file:mr-3 file:rounded-lg file:border-0 file:bg-slate-100 file:px-3 file:py-2 file:text-sm file:text-slate-700"
        />
        <button
          onClick={runImport}
          disabled={busy || !file}
          className="rounded-lg bg-gradient-to-r from-indigo-500 to-violet-500 px-4 py-2 text-sm font-medium text-white transition hover:opacity-90 disabled:opacity-40"
        >
          {busy ? "Importing..." : "Import users"}
        </button>
      </div>

      {error && (
        <p className="mt-3 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">
          {error}
        </p>
      )}

      {result && (
        <div className="mt-4">
          <div className="flex flex-wrap gap-3 text-sm">
            <span className="rounded-lg border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-900 px-3 py-1">
              Total rows: <b>{result.total_rows}</b>
            </span>
            <span className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-emerald-600 dark:text-emerald-300">
              Created: <b>{result.created}</b>
            </span>
            <span className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-1 text-amber-600 dark:text-amber-300">
              Skipped: <b>{result.skipped}</b>
            </span>
          </div>

          {result.results.length > 0 && (
            <div className="mt-3 overflow-x-auto rounded-xl border border-slate-200 dark:border-white/10">
              <table className="w-full text-left text-sm">
                <thead className="bg-white dark:bg-slate-900 text-xs uppercase text-slate-500 dark:text-slate-400">
                  <tr>
                    <th className="px-3 py-2">Row</th>
                    <th className="px-3 py-2">Email</th>
                    <th className="px-3 py-2">Status</th>
                    <th className="px-3 py-2">Detail</th>
                    <th className="px-3 py-2">Temp password</th>
                  </tr>
                </thead>
                <tbody>
                  {result.results.map((r) => (
                    <tr key={r.row} className="border-t border-slate-200 dark:border-white/10">
                      <td className="px-3 py-2 text-slate-500 dark:text-slate-400">{r.row}</td>
                      <td className="px-3 py-2">{r.email ?? "-"}</td>
                      <td className="px-3 py-2">
                        {r.status === "created" ? (
                          <span className="text-emerald-600 dark:text-emerald-300">created</span>
                        ) : (
                          <span className="text-amber-600 dark:text-amber-300">skipped</span>
                        )}
                      </td>
                      <td className="px-3 py-2 text-slate-600 dark:text-slate-300">{r.detail}</td>
                      <td className="px-3 py-2">
                        {r.temp_password ? (
                          <code className="rounded bg-black/30 px-2 py-0.5 text-indigo-700 dark:text-indigo-200">
                            {r.temp_password}
                          </code>
                        ) : (
                          <span className="text-slate-600 dark:text-slate-300">-</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {result.results.some((r) => r.temp_password) && (
            <p className="mt-2 text-xs text-amber-600/80">
              Save these temporary passwords now - they are shown only once. Ask
              users to change them after first login.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
