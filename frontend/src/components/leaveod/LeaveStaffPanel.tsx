"use client";

// Staff panel: approval inbox (approve/reject) + bulk OD for events.
import { FormEvent, useEffect, useState } from "react";

import { ApiError } from "@/lib/api";
import SectionPicker from "./SectionPicker";
import {
  LeaveRequest,
  LeaveStatus,
  OD_CATEGORIES,
  STATUS_STYLES,
  createBulkOD,
  decideRequest,
  listRequests,
  prettyCategory,
} from "./leaveodApi";

const STATUS_FILTERS: (LeaveStatus | "all")[] = [
  "pending",
  "approved",
  "rejected",
  "cancelled",
  "all",
];

function StatusBadge({ status }: { status: LeaveStatus }) {
  return (
    <span
      className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLES[status]}`}
    >
      {status}
    </span>
  );
}

export default function LeaveStaffPanel() {
  const [sectionId, setSectionId] = useState<number | null>(null);
  const [statusFilter, setStatusFilter] = useState<LeaveStatus | "all">(
    "pending",
  );
  const [requests, setRequests] = useState<LeaveRequest[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);

  // Bulk OD form.
  const [studentIds, setStudentIds] = useState("");
  const [category, setCategory] = useState("fest");
  const [title, setTitle] = useState("");
  const [eventName, setEventName] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [bulkSaving, setBulkSaving] = useState(false);
  const [bulkMsg, setBulkMsg] = useState<string | null>(null);
  const [bulkError, setBulkError] = useState<string | null>(null);

  function load() {
    setLoading(true);
    setError(null);
    listRequests({
      sectionId,
      status: statusFilter === "all" ? null : statusFilter,
    })
      .then(setRequests)
      .catch((e) =>
        setError(e instanceof ApiError ? e.message : "Failed to load requests"),
      )
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sectionId, statusFilter]);

  async function onDecide(id: number, status: "approved" | "rejected") {
    setBusyId(id);
    try {
      const note =
        status === "rejected"
          ? (window.prompt("Reason for rejection (optional)") ?? undefined)
          : undefined;
      await decideRequest(id, status, note);
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Decision failed");
    } finally {
      setBusyId(null);
    }
  }

  async function onBulk(e: FormEvent) {
    e.preventDefault();
    setBulkMsg(null);
    setBulkError(null);
    const ids = studentIds
      .split(/[\s,]+/)
      .map((s) => Number(s.trim()))
      .filter((n) => Number.isInteger(n) && n > 0);
    if (ids.length === 0) {
      setBulkError("Enter at least one valid student id");
      return;
    }
    if (!title.trim() || !startDate || !endDate) {
      setBulkError("Title, start and end dates are required");
      return;
    }
    setBulkSaving(true);
    try {
      const res = await createBulkOD({
        student_ids: ids,
        category,
        title: title.trim(),
        event_name: eventName.trim() || null,
        start_date: startDate,
        end_date: endDate,
      });
      setBulkMsg(
        `Created ${res.created} OD record(s)` +
          (res.skipped.length ? `, skipped ${res.skipped.length}` : ""),
      );
      setStudentIds("");
      setTitle("");
      setEventName("");
      setStartDate("");
      setEndDate("");
      load();
    } catch (err) {
      setBulkError(err instanceof ApiError ? err.message : "Bulk OD failed");
    } finally {
      setBulkSaving(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Approval inbox */}
      <div className="rounded-lg border border-gray-200 p-4">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-sm font-semibold text-gray-700">
            Approval inbox
          </h2>
          <select
            value={statusFilter}
            onChange={(e) =>
              setStatusFilter(e.target.value as LeaveStatus | "all")
            }
            className="rounded border border-gray-300 px-2 py-1 text-sm"
          >
            {STATUS_FILTERS.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
        <div className="mb-3">
          <SectionPicker onSection={setSectionId} />
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}
        {loading ? (
          <p className="text-sm text-gray-500">Loading...</p>
        ) : requests.length === 0 ? (
          <p className="text-sm text-gray-500">No requests.</p>
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
                  {r.student_name ?? `Student #${r.student_id}`}
                  {r.section_name ? ` - ${r.section_name}` : ""} -{" "}
                  {prettyCategory(r.category)}
                  {r.event_name ? ` (${r.event_name})` : ""} - {r.start_date} to{" "}
                  {r.end_date} ({r.days}d)
                </p>
                {r.status === "pending" && (
                  <div className="mt-2 flex gap-2">
                    <button
                      disabled={busyId === r.id}
                      onClick={() => onDecide(r.id, "approved")}
                      className="rounded bg-green-600 px-2.5 py-1 text-xs font-medium text-white disabled:opacity-50"
                    >
                      Approve
                    </button>
                    <button
                      disabled={busyId === r.id}
                      onClick={() => onDecide(r.id, "rejected")}
                      className="rounded bg-red-600 px-2.5 py-1 text-xs font-medium text-white disabled:opacity-50"
                    >
                      Reject
                    </button>
                  </div>
                )}
                {r.review_note && (
                  <p className="mt-1 text-xs text-gray-400">
                    Note: {r.review_note}
                  </p>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Bulk OD */}
      <form
        onSubmit={onBulk}
        className="space-y-3 rounded-lg border border-gray-200 p-4"
      >
        <h2 className="text-sm font-semibold text-gray-700">
          Bulk OD (fest / group event)
        </h2>
        <p className="text-xs text-gray-500">
          Raise auto-approved on-duty for many students at once. Each gets their
          own record, so attendance condonation stays per-student.
        </p>
        {bulkError && <p className="text-sm text-red-600">{bulkError}</p>}
        {bulkMsg && <p className="text-sm text-green-700">{bulkMsg}</p>}

        <label className="block text-sm">
          <span className="block text-gray-600">
            Student IDs (comma or space separated)
          </span>
          <input
            value={studentIds}
            onChange={(e) => setStudentIds(e.target.value)}
            placeholder="6, 7, 8"
            className="mt-1 w-full rounded border border-gray-300 px-2 py-1"
          />
        </label>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <label className="text-sm">
            <span className="block text-gray-600">Category</span>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="mt-1 w-full rounded border border-gray-300 px-2 py-1"
            >
              {OD_CATEGORIES.map((c) => (
                <option key={c} value={c}>
                  {prettyCategory(c)}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm">
            <span className="block text-gray-600">Event name</span>
            <input
              value={eventName}
              onChange={(e) => setEventName(e.target.value)}
              placeholder="State Meet 2026"
              className="mt-1 w-full rounded border border-gray-300 px-2 py-1"
            />
          </label>
        </div>

        <label className="block text-sm">
          <span className="block text-gray-600">Title</span>
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Inter-college tournament"
            className="mt-1 w-full rounded border border-gray-300 px-2 py-1"
          />
        </label>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
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
        </div>

        <button
          type="submit"
          disabled={bulkSaving}
          className="rounded bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
        >
          {bulkSaving ? "Creating..." : "Create bulk OD"}
        </button>
      </form>
    </div>
  );
}
