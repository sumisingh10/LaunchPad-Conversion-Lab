"use client";

/**
 * Module overview for frontend/app/campaigns/[id]/page.tsx.
 * Implements user-facing UI behavior for this route or component.
 */

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";

export default function CampaignHubPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const id = Number(params.id);
  const [name, setName] = useState("Campaign");

  useEffect(() => {
    if (!Number.isNaN(id)) api.getCampaign(id).then((c) => setName(c.name)).catch(() => setName("Campaign"));
  }, [id]);

  useEffect(() => {
    if (!Number.isNaN(id)) {
      router.replace(`/campaigns/${id}/build`);
    }
  }, [id, router]);

  return (
    <div className="space-y-4">
      <div className="rounded-2xl bg-gradient-to-r from-slate-900 via-slate-800 to-teal-800 p-6 text-white">
        <Link href="/campaigns" className="text-xs underline underline-offset-4">
          ← Back to campaigns
        </Link>
        <h1 className="mt-2 text-3xl font-bold">{name}</h1>
        <p className="text-sm text-slate-200">Choose where to go next.</p>
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        <Link href={`/campaigns/${id}/build`} className="rounded-2xl border bg-white p-5 shadow-sm hover:border-emerald-500">
          <p className="text-xs uppercase text-slate-500">Step 1</p>
          <p className="text-lg font-semibold text-slate-900">Build</p>
          <p className="text-sm text-slate-600">Generate recommendations, highlight page changes, and save variants.</p>
        </Link>
        <Link href={`/campaigns/${id}/compare`} className="rounded-2xl border bg-white p-5 shadow-sm hover:border-emerald-500">
          <p className="text-xs uppercase text-slate-500">Step 2</p>
          <p className="text-lg font-semibold text-slate-900">Compare</p>
          <p className="text-sm text-slate-600">Simulate KPI outcomes and ask Codex which variant best fits your goal.</p>
        </Link>
      </div>
    </div>
  );
}
