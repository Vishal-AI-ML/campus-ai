"use client";

// Student panel: apply for leave / OD and track your own requests.
import { FormEvent, useEffect, useState } from "react";

import { ApiError } from "@/lib/api";
import {
  LEAVE_CATEGORIES,
  LeaveRequest,
  OD_CATEGORIES,
  RequestType,
  STATUS_STYLES,
  applyLeave,
  cancelRequest,
  myRequests,
  prettyCategory,
} from "./leaveodApi";

function StatusBadge({ status }: { status: LeaveRequest["status"] }) {
  return (
    <span
      className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLES[status]}`}
    >
      {status}
    </span>
  );
}

export default function LeaveStudentPanel() {
  const [requests, setRequests] = useState<LeaveRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [requestType, setRequestType] = useState<RequestType>("leave");
  const [category, setCategory] = useState("medical");
  const [title, setTitle] = useState("");
  const [reason, setReason] = useState("");
  const [eventName, setEventName] = useState("");
  const [proofUrl, setProofUrl] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const categories = requestType === "od" ? OD_CATEGORIES : LEAVE_CATEGORIES;

  function load() {
    setLoading(true);
    myRequests()
      .then(setRequests)
      .catch((e) =>
        setError(e instanceof ApiError ? e.message : "Failed to load requests"),
      )
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    load();
  }, []);

  // Keep category valid when the type switches.
  useEffect(() => {
    const list = requestType === "od" ? OD_CATEGORIES : LEAVE_CATEGORIES;
    if (!list.includes(category)) setCategory(list[0]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [requestType]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    if (!title.trim() || !startDate || !endDate) {
      setFormError("Title, start and end dates are required");
      return;
    }
    setSaving(true);
    try {
      await applyLeave({
        request_type: requestType,
        category,
        title: title.trim(),
        reason: reason.trim() || null,
        event_name: requestType === "od" ? eventName.trim() || null : null,
        proof_url: proofUrl.trim() || null,
        start_date: startDate,
        end_date: endDate,
      });
      setTitle("");
      setReason("");
      setEventName("");
      setProofUrl("");
      setStartDate("");
      setEndDate("");
      load();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "Failed to apply");
    } finally {
      setSaving(false);
    }
  }

  async function onCancel(id: number) {
    try {
      await cancelRequest(id);
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to cancel");
    }
  }

  return (
    <div className="space-y-6">
      <form
        onSubmit={onSubmit}
        className="space-y-3 rounded-lg border border-gray-200 p-4"
      >
        <h2 className="text-sm font-semibold text-gray-700">
          Apply for leave / OD
        </h2>
        {formError && <p className="text-sm text-red-600">{formError}</p>}

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <label className="text-sm">
            <span className="block text-gray-600">Type</span>
            <select
              value={requestType}
              onChange={(e) => setRequestType(e.target.value as RequestType)}
              className="mt-1 w-full rounded border border-gray-300 px-2 py-1"
            >
              <option value="leave">Leave (personal)</option>
              <option value="od">OD (official duty)</option>
            </select>
          </label>
          <label className="text-sm">
            <span className="block text-gray-600">Category</span>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="mt-1 w-full rounded border border-gray-300 px-2 py-1"
            >
              {categories.map((c) => (
                <option key={c} value={c}>
                  {prettyCategory(c)}
                </option>
              ))}
            </select>
          </label>
        </div>

        <label className="block text-sm">
          <span className="block text-gray-600">Title</span>
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder={
              requestType === "od"
                ? "Volunteer at Spring Fest"
                : "Fever - need rest"
            }
            className="mt-1 w-full rounded border border-gray-300 px-2 py-1"
          />
        </label>

        {requestType === "od" && (
          <label className="block text-sm">
            <span className="block text-gray-600">Event name</span>
            <input
              value={eventName}
              onChange={(e) => setEventName(e.target.value)}
              placeholder="Spring Fest 2026"
              className="mt-1 w-full rounded border border-gray-300 px-2 py-1"
            />
          </label>
        )}

        <label className="block text-sm">
          <span className="block text-gray-600">Reason (optional)</span>
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            rows={2}
            className="mt-1 w-full rounded border border-gray-300 px-2 py-1"
          />
        </label>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <label className="text-sm">
            <span className="block text-gray-600">Start date</span>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="mt-1 w-full rounded border border-gray-300 px-2 py-1"
            />
          </label>
          <label className="text-sm">
            <span className="block text-gray-600">End date</span>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="mt-1 w-full rounded border border-gray-300 px-2 py-1"
            />
          </label>
          <label className="text-sm">
            <span className="block text-gray-600">Proof URL (optional)</span>
            <input
              value={proofUrl}
              onChange={(e) => setProofUrl(e.target.value)}
              placeholder="https://..."
              className="mt-1 w-full rounded border border-gray-300 px-2 py-1"
            />
          </label>
        </div>

        <button
          type="submit"
          disabled={saving}
          className="rounded bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
        >
          {saving ? "Submitting..." : "Submit request"}
        </button>
      </form>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <div className="rounded-lg border border-gray-200 p-4">
        <h2 className="mb-3 text-sm font-semibold text-gray-700">
          My requests
        </h2>
        {loading ? (
          <p className="text-sm text-gray-500">Loading...</p>
        ) : requests.length === 0 ? (
          <p className="text-sm text-gray-500">No requests yet.</p>
        ) : (
          <ul className="space-y-2">
            {requests.map((r) => (
              <li
                key={r.id}
                className="rounded border border-gray-200 px-3 py-2"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="rounded bg-gray-100 px-1.5 py-0.5 text-xs font-semibold uppercase text-gray-600">
                      {r.request_type}
                    </span>
                    <span className="font-medium text-gray-800">{r.title}</span>
                  </div>
                  <StatusBadge status={r.status} />
                </div>
                <p className="mt-1 text-sm text-gray-500">
                  {prettyCategory(r.category)}
                  {r.event_name ? ` - ${r.event_name}` : ""} - {r.start_date} to{" "}
                  {r.end_date} ({r.days} day{r.days > 1 ? "s" : ""})
                </p>
                {r.review_note && (
                  <p className="mt-1 text-sm text-gray-500">
                    Note: {r.review_note}
                    {r.reviewer_name ? ` - ${r.reviewer_name}` : ""}
                  </p>
                )}
                {(r.status === "pending" || r.status === "approved") && (
                  <button
                    onClick={() => onCancel(r.id)}
                    className="mt-2 text-sm text-red-600 hover:underline"
                  >
                    Cancel
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
