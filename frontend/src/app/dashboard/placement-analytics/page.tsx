"use client";

// Route: /dashboard/placement-analytics
// TPO + admin: program-wide placement funnel, rate, per-drive + company stats.
import { useEffect, useState } from "react";

import { ApiError } from "@/lib/api";
import {
  MeUser,
  getMe,
} from "@/components/placement-analytics/placementAnalyticsApi";
import PlacementAnalyticsPanel from "@/components/placement-analytics/PlacementAnalyticsPanel";

const ICON = "\u{1F4C8}";

export default function PlacementAnalyticsPage() {
  const [me, setMe] = useState<MeUser | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getMe()
      .then(setMe)
      .catch((e) =>
        setError(e instanceof ApiError ? e.message : "Failed to load profile"),
      );
  }, []);

  const isStaff = me?.role === "tpo" || me?.role === "admin";

  return (
    <div className="mx-auto max-w-5xl p-6">
      <h1 className="mb-1 text-2xl font-bold text-gray-900">
        {ICON} Placement Analytics
      </h1>
      <p className="mb-6 text-sm text-gray-500">
        Recruitment funnel, placement rate, and per-drive + company outcomes.
      </p>
      {error && <p className="text-sm text-red-600">{error}</p>}
      {!me ? (
        <p className="text-sm text-gray-500">Loading...</p>
      ) : isStaff ? (
        <PlacementAnalyticsPanel />
      ) : (
        <p className="text-sm text-gray-500">
          Placement analytics is available to TPO and admin only.
        </p>
      )}
    </div>
  );
}
