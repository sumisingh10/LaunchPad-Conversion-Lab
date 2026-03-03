"use client";

/**
 * Module overview for frontend/app/campaigns/[id]/build/page.tsx.
 * Implements user-facing UI behavior for this route or component.
 */

import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { toJpeg } from "html-to-image";

import { LoadingOverlay } from "@/components/LoadingOverlay";
import { IdlePrompt } from "@/components/IdlePrompt";
import { StorefrontCanvas } from "@/components/StorefrontCanvas";
import { api } from "@/lib/api";
import { Campaign, Recommendation, Variant } from "@/lib/types";

function applyPatchToAssets(baseAssets: any, patchJson: any) {
  const updated = JSON.parse(JSON.stringify(baseAssets));
  for (const operation of patchJson?.operations || []) {
    const path = String(operation.path || "").split(".");
    let cursor = updated;
    for (let i = 0; i < path.length; i++) {
      const part = path[i];
      const isLast = i === path.length - 1;
      if (/^\d+$/.test(part)) {
        const idx = Number(part);
        if (isLast) cursor[idx] = operation.value;
        else cursor = cursor[idx];
      } else {
        if (isLast) cursor[part] = operation.value;
        else cursor = cursor[part];
      }
    }
  }
  return updated;
}

function humanLabel(text: string) {
  return text
    .replace(/\./g, " ")
    .replace(/_/g, " ")
    .replace(/\bcta\b/gi, "CTA")
    .replace(/\bhero\b/gi, "")
    .replace(/\bbanner\b/gi, "promo banner")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function humanizeCopy(text: string) {
  return text
    .replace(/\bCTR\b/g, "click-through rate")
    .replace(/\bCTA\b/g, "click-through action");
}

function variantDisplayName(variant: Variant, baselineVariantId: number | null) {
  if (variant.id === baselineVariantId) return "Baseline";
  if (variant.name.trim().toLowerCase() === "baseline") return `Variant #${variant.id}`;
  return variant.name;
}

export default function BuildPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const searchParams = useSearchParams();
  const id = Number(params.id);
  const [campaign, setCampaign] = useState<Campaign | null>(null);
  const [variants, setVariants] = useState<Variant[]>([]);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [selectedVariantId, setSelectedVariantId] = useState<number | null>(null);
  const [previewRecommendationId, setPreviewRecommendationId] = useState<number | null>(null);
  const [focusComponent, setFocusComponent] = useState<string | null>(null);
  const [assistantPrompt, setAssistantPrompt] = useState("");
  const [snapshotUrl, setSnapshotUrl] = useState<string | null>(null);
  const [variantName, setVariantName] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [actionTick, setActionTick] = useState(0);
  const [hasRequestedRecommendations, setHasRequestedRecommendations] = useState(false);
  const [approvalState, setApprovalState] = useState<{
    status: "NOT_SUBMITTED" | "PENDING_ADMIN_APPROVAL" | "APPROVED";
    message: string;
    seconds_until_auto_approval?: number | null;
  } | null>(null);
  const [approvalStatus, setApprovalStatus] = useState<string | null>(null);
  const [pendingNavHref, setPendingNavHref] = useState<string | null>(null);
  const canvasRef = useRef<HTMLDivElement | null>(null);

  async function refresh(preferredVariantId?: number, preferredRecommendationId?: number) {
    let [c, v, r] = await Promise.all([api.getCampaign(id), api.listVariants(id), api.listRecommendations(id)]);
    if (!v.length) {
      try {
        await api.generateVariants(id);
        [c, v, r] = await Promise.all([api.getCampaign(id), api.listVariants(id), api.listRecommendations(id)]);
      } catch {
        // Keep UI usable even if variant generation fails.
      }
    }
    setCampaign(c);
    setVariants(v);
    setRecommendations(r);
    const hasActiveProposals = r.some((item) => item.status === "PROPOSED");
    if (hasActiveProposals && !hasRequestedRecommendations) {
      setHasRequestedRecommendations(true);
    }
    if (!v.length) {
      setSelectedVariantId(null);
      setPreviewRecommendationId(null);
      setApprovalState(null);
      return;
    }

    const preferredFromQuery = Number(searchParams.get("variantId") || 0) || undefined;
    const baselineId = Number(c.constraints_json?.baseline_variant_id || 0) || null;
    const nextVariantId =
      preferredFromQuery && v.some((item) => item.id === preferredFromQuery)
        ? preferredFromQuery
        : preferredVariantId && v.some((item) => item.id === preferredVariantId)
        ? preferredVariantId
        : selectedVariantId && v.some((item) => item.id === selectedVariantId)
          ? selectedVariantId
          : baselineId && v.some((item) => item.id === baselineId)
            ? baselineId
            : v[0].id;
    setSelectedVariantId(nextVariantId);

    if (!hasRequestedRecommendations && !hasActiveProposals) {
      setPreviewRecommendationId(null);
      return;
    }
    const activeProposals = r.filter((item) => item.status === "PROPOSED");
    const nextRecommendationId =
      preferredRecommendationId && activeProposals.some((item) => item.id === preferredRecommendationId)
        ? preferredRecommendationId
        : previewRecommendationId && activeProposals.some((item) => item.id === previewRecommendationId)
          ? previewRecommendationId
          : activeProposals.find((item) => item.variant_id === nextVariantId)?.id ?? activeProposals[0]?.id ?? null;
    setPreviewRecommendationId(nextRecommendationId);
  }

  useEffect(() => {
    if (!Number.isNaN(id)) refresh();
  }, [id, searchParams]);

  useEffect(() => {
    let cancelled = false;
    async function loadApprovalStatus() {
      if (!selectedVariantId) {
        setApprovalState(null);
        return;
      }
      try {
        const status = await api.getVariantAdminApprovalStatus(selectedVariantId);
        if (!cancelled) setApprovalState(status);
      } catch {
        if (!cancelled) setApprovalState(null);
      }
    }
    loadApprovalStatus();
    return () => {
      cancelled = true;
    };
  }, [selectedVariantId]);

  useEffect(() => {
    setApprovalStatus(null);
  }, [selectedVariantId]);

  useEffect(() => {
    if (!selectedVariantId || approvalState?.status !== "PENDING_ADMIN_APPROVAL") return;
    let cancelled = false;
    const interval = setInterval(async () => {
      try {
        const status = await api.getVariantAdminApprovalStatus(selectedVariantId);
        if (!cancelled) setApprovalState(status);
      } catch {
        // Ignore transient polling errors.
      }
    }, 2000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [selectedVariantId, approvalState?.status]);

  const selectedVariant = useMemo(() => variants.find((v) => v.id === selectedVariantId) || null, [variants, selectedVariantId]);
  const previewRecommendation = useMemo(
    () => recommendations.find((r) => r.id === previewRecommendationId) || null,
    [recommendations, previewRecommendationId]
  );
  const visibleProposals = useMemo(
    () => {
      if (!hasRequestedRecommendations) return [];
      const allowed = new Set(variants.map((v) => v.id));
      return recommendations
        .filter((r) => r.status === "PROPOSED" && allowed.has(r.variant_id))
        .slice(0, 3);
    },
    [hasRequestedRecommendations, recommendations, variants]
  );

  const previewVariant = useMemo(() => {
    if (!selectedVariant) return null;
    if (!previewRecommendation || previewRecommendation.variant_id !== selectedVariant.id) return selectedVariant;
    return { ...selectedVariant, assets_json: applyPatchToAssets(selectedVariant.assets_json, previewRecommendation.patch_json) };
  }, [selectedVariant, previewRecommendation]);
  const baselineVariantId = Number(campaign?.constraints_json?.baseline_variant_id || 0) || null;
  const selectedIsBaseline = !!selectedVariant && selectedVariant.id === baselineVariantId;
  const canSubmitAdminApproval = selectedVariant?.source === "CODEX_PATCHED" && !selectedIsBaseline;
  const selectedIsApproved = approvalState?.status === "APPROVED";
  const selectedIsPending = approvalState?.status === "PENDING_ADMIN_APPROVAL";

  function hasUnsavedDraft() {
    return assistantPrompt.trim().length > 0 || variantName.trim().length > 0;
  }

  async function captureSnapshot() {
    if (!canvasRef.current) return undefined;
    const data = await toJpeg(canvasRef.current, { quality: 0.7, cacheBust: true, pixelRatio: 1 });
    setSnapshotUrl(data);
    return data;
  }

  if (!campaign) return <div className="rounded-xl border bg-white p-6 text-sm text-slate-500">Loading build studio...</div>;

  return (
    <div className="space-y-4">
      <LoadingOverlay
        show={!!busy}
        message={
          busy === "recommend"
            ? "Capturing storefront and asking Codex for recommendations..."
            : busy === "save"
              ? "Saving variant version..."
              : busy === "delete"
                ? "Deleting variant and refreshing campaign state..."
              : "Working..."
        }
      />
      <div className="flex items-center justify-between rounded-2xl border border-slate-200/70 bg-white/75 p-4 shadow-[0_10px_30px_rgba(15,23,42,0.06)] backdrop-blur">
        <div>
          <p className="text-xs uppercase text-slate-500">Build Studio</p>
          <h1 className="text-2xl font-semibold text-slate-900">{campaign.name}</h1>
        </div>
        <div className="flex gap-2">
          <Link
            href="/campaigns"
            className="rounded border bg-white px-3 py-2 text-sm"
            onClick={(e) => {
              if (!hasUnsavedDraft()) return;
              e.preventDefault();
              setPendingNavHref("/campaigns");
            }}
          >
            Campaigns
          </Link>
          <Link
            href={`/campaigns/${id}/compare`}
            className="rounded bg-slate-900 px-3 py-2 text-sm text-white"
            onClick={(e) => {
              if (!hasUnsavedDraft()) return;
              e.preventDefault();
              setPendingNavHref(`/campaigns/${id}/compare`);
            }}
          >
            Go To Compare
          </Link>
        </div>
      </div>

      <IdlePrompt
        active={!busy}
        actionTick={actionTick}
        tips={[
          "Ask Codex for recommendations to bootstrap your first proposal set.",
          "Use 'Ask Codex For Recommendations' to highlight page sections that can be improved.",
          "After you preview a suggestion, click 'Mark This Change and Save Variant' to keep a testable change."
        ]}
      />

      <div className="grid gap-4 lg:grid-cols-[1.9fr_0.75fr]">
        <div className="space-y-3">
          <div className="flex flex-wrap gap-2 rounded-xl border border-slate-200/80 bg-white/80 p-2 shadow-sm backdrop-blur">
            <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs text-slate-600">
              Viewing Variant
            </div>
            <select
              className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"
              value={selectedVariantId || ""}
              onChange={(e) => {
                const nextVariantId = Number(e.target.value);
                setSelectedVariantId(nextVariantId);
                const firstForVariant = visibleProposals.find((proposal) => proposal.variant_id === nextVariantId);
                setPreviewRecommendationId(firstForVariant?.id ?? null);
              }}
            >
              {variants.map((v) => (
                <option key={v.id} value={v.id}>
                  {variantDisplayName(v, baselineVariantId)}
                </option>
              ))}
            </select>
            <button
              className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs font-semibold text-rose-700 disabled:cursor-not-allowed disabled:opacity-50"
              disabled={!selectedVariant || selectedIsBaseline || !!busy}
              onClick={async () => {
                if (!selectedVariant) return;
                if (!confirm(`Delete variant '${selectedVariant.name}'? This removes its KPI and recommendation history.`)) return;
                setBusy("delete");
                setError(null);
                try {
                  await api.deleteVariant(selectedVariant.id);
                  setPreviewRecommendationId(null);
                  setFocusComponent(null);
                  setAssistantPrompt("");
                  setVariantName("");
                  await refresh();
                  setActionTick((v) => v + 1);
                } catch (err: any) {
                  setError(err.message || "Unable to delete variant");
                } finally {
                  setBusy(null);
                }
              }}
              title={selectedIsBaseline ? "Baseline variants cannot be deleted." : "Delete this variant"}
            >
              Delete Variant
            </button>
          </div>
          <div ref={canvasRef}>
            <StorefrontCanvas
              variant={previewVariant}
              highlightPath={previewRecommendation?.target_component || focusComponent || "hero.headline"}
              onSelectArea={(path) => {
                setFocusComponent(path);
                setPreviewRecommendationId(null);
                setAssistantPrompt(`Optimize ${humanLabel(path)} for this audience.`);
              }}
            />
          </div>
          {previewRecommendation ? (
            <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm">
              <p className="font-semibold text-emerald-900">Active proposal on page</p>
              <p className="text-emerald-800">{previewRecommendation.rationale}</p>
              <p className="mt-1 text-xs text-emerald-900">Highlighted area: {humanLabel(previewRecommendation.target_component)}</p>
            </div>
          ) : null}
          {focusComponent && !previewRecommendation ? (
            <div className="rounded-xl border border-sky-200 bg-sky-50 p-3 text-sm">
              <p className="font-semibold text-sky-900">Selected area for optimization</p>
              <p className="text-sky-800">{humanLabel(focusComponent)}</p>
            </div>
          ) : null}
          {snapshotUrl ? <p className="text-xs text-slate-500">Live storefront snapshot captured for this recommendation run.</p> : null}
          {selectedVariantId && approvalState && !selectedIsBaseline ? (
            <p className="text-xs text-emerald-700">
              {approvalState.message}
              {selectedIsPending && typeof approvalState.seconds_until_auto_approval === "number"
                ? ` Auto-approval in ~${approvalState.seconds_until_auto_approval}s.`
                : ""}
            </p>
          ) : null}
        </div>

        <div className="space-y-3">
          <div className="rounded-xl border bg-white p-3">
            <p className="text-sm font-semibold text-slate-900">Assistant</p>
            <p className="text-xs text-slate-600">Tell Codex what to optimize, then generate and preview changes.</p>
            <textarea
              className="mt-2 w-full rounded border p-2 text-sm"
              rows={3}
              placeholder="Example: Keep premium tone and reduce bounce for mobile shoppers."
              value={assistantPrompt}
              onChange={(e) => setAssistantPrompt(e.target.value)}
            />
            <div className="mt-2 flex gap-2">
              <button
                className="rounded bg-slate-900 px-3 py-2 text-xs text-white"
                onClick={async () => {
                  setError(null);
                  setBusy("recommend");
                  try {
                    if (variants.length === 0) {
                      await api.generateVariants(id);
                    }
                    const snap = await captureSnapshot();
                    setHasRequestedRecommendations(true);
                    await api.propose(id, {
                      user_goal: assistantPrompt || "Improve conversion quality while keeping brand clarity.",
                      landing_page_snapshot_url: snap,
                      focus_component: focusComponent || undefined,
                      selected_variant_id: selectedVariantId || undefined,
                    });
                    await refresh(undefined, undefined);
                    setActionTick((v) => v + 1);
                    setVariantName("");
                  } catch (e: any) {
                    setError(e?.message || "Unable to generate recommendations. Please try again.");
                  } finally {
                    setBusy(null);
                  }
                }}
              >
                Ask Codex For Recommendations
              </button>
            </div>
          </div>

          <div className="rounded-xl border bg-white p-3">
            <p className="text-sm font-semibold text-slate-900">Proposed Improvements</p>
            <p className="text-xs text-slate-600">Select a proposal to highlight it on the storefront. Apply when ready.</p>
            {selectedVariant?.source === "CODEX_PATCHED" ? (
              <p className="mt-2 rounded border border-amber-300 bg-amber-50 px-2 py-1 text-xs text-amber-800">
                A/B test policy: one proposal can be applied at a time to keep attribution clean.
              </p>
            ) : null}
            <div className="mt-2 space-y-2">
              {visibleProposals.length === 0 ? (
                <p className="rounded bg-slate-50 px-2 py-2 text-xs text-slate-500">No active proposals yet. Ask Codex to generate them.</p>
              ) : (
                visibleProposals.map((proposal) => (
                  <button
                    key={proposal.id}
                    data-testid={`proposal-${proposal.id}`}
                    className={`w-full rounded border px-2 py-2 text-left text-xs ${previewRecommendationId === proposal.id ? "border-emerald-500 bg-emerald-50" : "bg-white"}`}
                    onClick={() => {
                      if (previewRecommendationId === proposal.id) {
                        setPreviewRecommendationId(null);
                        return;
                      }
                      setPreviewRecommendationId(proposal.id);
                      setSelectedVariantId(proposal.variant_id);
                    }}
                  >
                    <p className="font-semibold text-slate-900">
                      {humanLabel(proposal.change_type)} · {humanLabel(proposal.target_component)}
                      {proposal.status === "APPLIED" ? <span className="ml-1 rounded bg-slate-100 px-1 py-0.5 text-[10px] text-slate-600">Saved</span> : null}
                    </p>
                    <p className="text-slate-600">{humanizeCopy(proposal.hypothesis)}</p>
                  </button>
                ))
              )}
            </div>
            <input
              className="mt-2 w-full rounded border p-2 text-xs"
              placeholder="Name this variant (required)"
              value={variantName}
              onChange={(e) => setVariantName(e.target.value)}
            />
            <button
              className="mt-2 w-full rounded bg-emerald-700 px-3 py-2 text-sm text-white disabled:opacity-60"
              disabled={!previewRecommendationId || !variantName.trim()}
              onClick={async () => {
                if (!previewRecommendationId) return;
                setError(null);
                const normalized = variantName.trim().toLowerCase();
                if (!normalized) {
                  setError("Please enter a variant name before saving this change.");
                  return;
                }
                if (variants.some((variant) => variant.name.trim().toLowerCase() === normalized)) {
                  setError("Variant name already exists. Please choose a unique name.");
                  return;
                }
                setBusy("save");
                try {
                  const createdVariant = await api.saveRecommendationVariant(
                    previewRecommendationId,
                    { variant_name: variantName.trim() }
                  );
                  await refresh(createdVariant.id, undefined);
                  setActionTick((v) => v + 1);
                  setVariantName("");
                } catch (e: any) {
                  setError(e?.message || "Unable to save this variant.");
                } finally {
                  setBusy(null);
                }
              }}
            >
              Mark This Change and Save Variant
            </button>
            <button
              className="mt-2 w-full rounded border border-indigo-200 bg-indigo-50 px-3 py-2 text-sm text-indigo-800 disabled:opacity-60"
              disabled={!selectedVariantId || !canSubmitAdminApproval}
              onClick={async () => {
                if (!selectedVariantId) return;
                setError(null);
                setApprovalStatus(null);
                if (selectedIsApproved) {
                  setApprovalStatus("Already approved. No further submission needed.");
                  return;
                }
                setBusy("save");
                try {
                  const response = await api.submitVariantForAdminApproval(selectedVariantId);
                  setApprovalStatus(response?.message || "Submitted for website admin approval.");
                  await refresh(selectedVariantId, previewRecommendationId || undefined);
                  const latestStatus = await api.getVariantAdminApprovalStatus(selectedVariantId);
                  setApprovalState(latestStatus);
                } catch (e: any) {
                  setError(e?.message || "Unable to submit this variant for admin approval.");
                } finally {
                  setBusy(null);
                }
              }}
            >
              Submit For Admin Approval
            </button>
            {selectedIsBaseline ? (
              <p className="mt-2 text-xs text-slate-500">
                Baseline is already active and does not require admin approval.
              </p>
            ) : !canSubmitAdminApproval ? (
              <p className="mt-2 text-xs text-slate-500">
                Save a selected recommendation as a new variant before submitting for admin approval.
              </p>
            ) : null}
            {approvalStatus ? <p className="mt-2 rounded border border-indigo-200 bg-indigo-50 px-2 py-1 text-xs text-indigo-700">{approvalStatus}</p> : null}
            {error ? <p className="mt-2 rounded border border-rose-200 bg-rose-50 px-2 py-1 text-xs text-rose-700">{error}</p> : null}
          </div>
        </div>
      </div>
      {pendingNavHref ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/30 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-5 shadow-2xl">
            <p className="text-lg font-semibold text-slate-900">Keep your draft?</p>
            <p className="mt-2 text-sm text-slate-600">
              You have unsaved text in the assistant or variant name fields. Leaving this page now may lose that draft.
            </p>
            <div className="mt-4 flex justify-end gap-2">
              <button className="rounded border px-3 py-2 text-sm" onClick={() => setPendingNavHref(null)}>
                Stay Here
              </button>
              <button
                className="rounded bg-slate-900 px-3 py-2 text-sm text-white"
                onClick={() => {
                  const href = pendingNavHref;
                  setPendingNavHref(null);
                  if (href) router.push(href);
                }}
              >
                Continue
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
