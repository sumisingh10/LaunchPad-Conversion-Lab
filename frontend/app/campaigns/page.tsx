"use client";

/**
 * Module overview for frontend/app/campaigns/page.tsx.
 * Implements user-facing UI behavior for this route or component.
 */

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { CampaignForm } from "@/components/CampaignForm";
import { CodexStatusBadge } from "@/components/CodexStatusBadge";
import { StateBlock } from "@/components/StateBlock";
import { api } from "@/lib/api";
import { Campaign, CodexAuthStatus } from "@/lib/types";

export default function CampaignsPage() {
  const router = useRouter();
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [codexStatus, setCodexStatus] = useState<CodexAuthStatus | null>(null);
  const [showAllCampaigns, setShowAllCampaigns] = useState(false);

  async function load() {
    setLoading(true);
    try {
      setCampaigns(await api.listCampaigns());
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    api.codexAuthStatus().then(setCodexStatus).catch(() => setCodexStatus(null));
  }, []);

  function objectiveLabel(value: string) {
    if (value === "CTR") return "Click-through Rate";
    if (value === "ATC") return "Add-to-cart Rate";
    if (value === "CONVERSION") return "Conversion";
    return value;
  }

  const sortedCampaigns = [...campaigns].sort((a, b) => b.id - a.id);
  const curatedCampaigns = sortedCampaigns.filter(
    (campaign) => !/(^e2e\b|\bdemo\b)/i.test(campaign.name.trim())
  );
  const baseCampaigns = curatedCampaigns.length ? curatedCampaigns : sortedCampaigns;
  const displayCampaigns = showAllCampaigns ? baseCampaigns : baseCampaigns.slice(0, 4);

  return (
    <div className="space-y-5">
      <div className="relative overflow-hidden rounded-3xl border border-slate-200/70 bg-gradient-to-r from-sky-100 via-cyan-50 to-emerald-100 p-7 shadow-[0_18px_50px_rgba(15,23,42,0.08)]">
        <div className="pointer-events-none absolute -right-10 -top-14 h-48 w-48 rounded-full bg-sky-300/25 blur-3xl" />
        <div className="pointer-events-none absolute -left-8 -bottom-12 h-44 w-44 rounded-full bg-emerald-300/20 blur-3xl" />
        <h1 className="text-3xl font-semibold tracking-tight text-slate-900">LaunchPad Conversion Lab</h1>
        <p className="mt-2 max-w-2xl text-sm text-slate-700">
          Start from one campaign, craft page variants with Codex, then compare KPI lift in a clean test loop.
        </p>
        <div className="mt-3">
          <CodexStatusBadge status={codexStatus} />
        </div>
      </div>
      <div className="rounded-2xl border border-slate-200/80 bg-white/80 p-4 shadow-[0_8px_30px_rgba(15,23,42,0.05)] backdrop-blur">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <p className="text-sm font-semibold text-slate-900">Campaign Workspace</p>
            <p className="text-xs text-slate-600">Start from a focused campaign to keep testing flow clear.</p>
          </div>
          <button className="rounded-lg bg-slate-800 px-3 py-2 text-xs text-white" onClick={() => setShowCreate((v) => !v)}>
            {showCreate ? "Hide Create Form" : "Create New Campaign"}
          </button>
        </div>
        {showCreate ? (
          <div className="mt-3">
            <CampaignForm
              onSubmit={async (payload) => {
                await api.createCampaign(payload);
                await load();
                setShowCreate(false);
              }}
            />
          </div>
        ) : null}
      </div>
      {loading ? <StateBlock message="Loading campaigns..." /> : null}
      {error ? <StateBlock message={`Error: ${error}`} /> : null}
      {!loading && campaigns.length === 0 ? <StateBlock message="No campaigns yet" /> : null}
      {campaigns.length > 0 ? (
        <>
          <div className="flex flex-wrap items-center justify-between gap-2 rounded-2xl border border-slate-200/80 bg-white/80 p-3 shadow-[0_6px_20px_rgba(15,23,42,0.04)]">
            <p className="text-xs text-slate-600">
              Showing {displayCampaigns.length} of {baseCampaigns.length} campaigns
            </p>
            <div className="flex flex-wrap items-center gap-2">
              {baseCampaigns.length > 4 ? (
                <button
                  className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-700"
                  onClick={() => setShowAllCampaigns((v) => !v)}
                >
                  {showAllCampaigns ? "Show Top 4 Campaigns" : "Show All Campaigns"}
                </button>
              ) : null}
              <select
                defaultValue=""
                className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs text-slate-700"
                onChange={(e) => {
                  const campaignId = Number(e.target.value);
                  if (!campaignId) return;
                  router.push(`/campaigns/${campaignId}/build`);
                }}
              >
                <option value="">Jump to campaign...</option>
                {baseCampaigns.map((campaign) => (
                  <option key={`jump-${campaign.id}`} value={campaign.id}>
                    {campaign.name}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
          {displayCampaigns.map((campaign, idx) => (
            <div key={campaign.id} className="rounded-2xl border border-slate-200/80 bg-white/85 p-5 shadow-[0_8px_24px_rgba(15,23,42,0.05)] transition hover:-translate-y-0.5 hover:border-sky-300">
              <p className="text-xs uppercase tracking-wide text-slate-500">{idx === 0 ? "Featured Campaign" : "Campaign"}</p>
              <p className="mt-1 text-xl font-semibold tracking-tight text-slate-900">{campaign.name}</p>
              <p className="text-sm text-slate-600">{campaign.product_title} · {campaign.audience_segment}</p>
              <p className="mt-1 text-xs text-slate-500">
                Objective: {objectiveLabel(campaign.objective)}
              </p>
              <div className="mt-3 flex gap-2">
                <Link href={`/campaigns/${campaign.id}/build`} className="inline-flex rounded-lg bg-slate-900 px-3 py-2 text-xs font-semibold text-white">
                  Open Campaign
                </Link>
                <button
                  className="inline-flex rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs font-semibold text-rose-700"
                  onClick={async () => {
                    if (!confirm(`Delete campaign '${campaign.name}'? This cannot be undone.`)) return;
                    await api.deleteCampaign(campaign.id);
                    await load();
                  }}
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
          </div>
        </>
      ) : null}
    </div>
  );
}
