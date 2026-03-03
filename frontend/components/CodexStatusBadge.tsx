"use client";

/**
 * Module overview for frontend/components/CodexStatusBadge.tsx.
 * Displays high-level Codex connectivity state for presenter/demo confidence.
 */

import { CodexAuthStatus } from "@/lib/types";

export function CodexStatusBadge({ status }: { status: CodexAuthStatus | null }) {
  if (!status) {
    return <div className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs text-slate-600">Checking Codex status...</div>;
  }

  const connected = status.connected;
  const tone = connected
    ? "border-emerald-200 bg-emerald-50 text-emerald-800"
    : "border-rose-200 bg-rose-50 text-rose-700";

  return (
    <div className={`rounded-full border px-3 py-1 text-xs ${tone}`}>
      Codex {connected ? "Connected" : "Not Connected"} · Provider: {status.provider.toUpperCase()} · Fallback:{" "}
      {status.fallback_enabled ? "On" : "Off"}
    </div>
  );
}

