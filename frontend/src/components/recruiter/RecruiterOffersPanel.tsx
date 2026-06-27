"use client";

/**
 * Recruiter offers panel (Step 27.4).
 *
 * Lists every offer the recruiter's company has extended, with status and the
 * student's response. Still-extended offers can be withdrawn; accepted ones
 * are locked (the backend returns 409, surfaced inline).
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { ApiError } from "@/lib/api";
import {
  OFFER_STYLES,
  fmtDate,
  fmtPackage,
  listMyOffers,
  pretty,
  withdrawOffer,
  type Offer,
  type OfferStatus,
} from "./recruiterApi";

type Filter = "all" | OfferStatus;

export default function RecruiterOffersPanel() {
  const [offers, setOffers] = useState<Offer[]>([]);
  const [filter, setFilter] = useState<Filter>("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<number | null>(null);
  const [rowErr, setRowErr] = useState<Record<number, string>>({});

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setOffers(await listMyOffers());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load offers.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const counts = useMemo(() => {
    const c: Record<string, number> = {
      extended: 0,
      accepted: 0,
      declined: 0,
      withdrawn: 0,
    };
    offers.forEach((o) => (c[o.status] = (c[o.status] ?? 0) + 1));
    return c;
  }, [offers]);

  const shown = useMemo(
    () => (filter === "all" ? offers : offers.filter((o) => o.status === filter)),
    [offers, filter],
  );

  async function doWithdraw(offer: Offer) {
    setBusy(offer.id);
    setRowErr((p) => ({ ...p, [offer.id]: "" }));
    try {
      const updated = await withdrawOffer(offer.id);
      setOffers((prev) => prev.map((o) => (o.id === updated.id ? updated : o)));
    } catch (e) {
      setRowErr((p) => ({
        ...p,
        [offer.id]: e instanceof ApiError ? e.message : "Could not withdraw.",
      }));
    } finally {
      setBusy(null);
    }
  }

  const FILTERS: Filter[] = [
    "all",
    "extended",
    "accepted",
    "declined",
    "withdrawn",
  ];

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold">Offers</h2>
          <p className="mt-1 text-sm text-slate-400">
            Offers your company has extended and their current status.
          </p>
        </div>
        <button
          onClick={load}
          className="rounded-lg border border-white/15 px-3 py-2 text-sm hover:bg-white/5"
        >
          Refresh
        </button>
      </div>

      <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Kpi label="Extended" value={counts.extended} accent="text-indigo-300" />
        <Kpi label="Accepted" value={counts.accepted} accent="text-emerald-300" />
        <Kpi label="Declined" value={counts.declined} accent="text-red-300" />
        <Kpi label="Withdrawn" value={counts.withdrawn} accent="text-slate-400" />
      </div>

      <div className="mt-6 flex flex-wrap gap-2">
        {FILTERS.map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`rounded-lg px-3 py-1.5 text-sm transition ${
              filter === f
                ? "bg-indigo-500 text-white"
                : "border border-white/15 hover:bg-white/5"
            }`}
          >
            {f === "all" ? "All" : pretty(f)}
          </button>
        ))}
      </div>

      {error && (
        <p className="mt-6 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">
          {error}
        </p>
      )}

      {loading ? (
        <p className="mt-8 text-sm text-slate-400">Loading offers...</p>
      ) : shown.length === 0 ? (
        <div className="mt-8 rounded-2xl border border-white/10 bg-white/5 p-8 text-center text-slate-400">
          No offers to show. Extend an offer from the Candidates page.
        </div>
      ) : (
        <div className="mt-6 overflow-x-auto rounded-2xl border border-white/10">
          <table className="w-full text-left text-sm">
            <thead className="bg-white/5 text-xs uppercase tracking-wide text-slate-400">
              <tr>
                <th className="px-4 py-3">Candidate</th>
                <th className="px-4 py-3">Role</th>
                <th className="px-4 py-3">Package</th>
                <th className="px-4 py-3">Location</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Response</th>
                <th className="px-4 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody>
              {shown.map((o) => (
                <tr key={o.id} className="border-t border-white/5">
                  <td className="px-4 py-3 font-medium">{o.student_name}</td>
                  <td className="px-4 py-3 text-slate-300">{o.role_title}</td>
                  <td className="px-4 py-3 text-slate-300">
                    {fmtPackage(o.package_lpa)}
                  </td>
                  <td className="px-4 py-3 text-slate-300">
                    {o.location ?? "\u2014"}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs ${OFFER_STYLES[o.status]}`}
                    >
                      {pretty(o.status)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-400">
                    {o.responded_at ? (
                      <span>
                        {fmtDate(o.responded_at)}
                        {o.student_response_note
                          ? ` \u2014 ${o.student_response_note}`
                          : ""}
                      </span>
                    ) : (
                      "Awaiting"
                    )}
                  </td>
                  <td className="px-4 py-3 text-right">
                    {o.status === "extended" ? (
                      <button
                        onClick={() => doWithdraw(o)}
                        disabled={busy === o.id}
                        className="rounded-lg border border-red-500/40 px-3 py-1.5 text-xs text-red-300 transition hover:bg-red-500/10 disabled:opacity-50"
                      >
                        {busy === o.id ? "..." : "Withdraw"}
                      </button>
                    ) : (
                      <span className="text-xs text-slate-600">—</span>
                    )}
                    {rowErr[o.id] && (
                      <p className="mt-1 text-xs text-red-300">{rowErr[o.id]}</p>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function Kpi({
  label,
  value,
  accent,
}: {
  label: string;
  value: number;
  accent: string;
}) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
      <div className={`text-2xl font-bold ${accent}`}>{value}</div>
      <div className="mt-1 text-xs text-slate-400">{label}</div>
    </div>
  );
}
