"use client";

/**
 * Module overview for frontend/app/campaigns/[id]/compare/page.tsx.
 * Implements user-facing UI behavior for this route or component.
 */

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { KPICharts } from "@/components/KPICharts";
import { IdlePrompt } from "@/components/IdlePrompt";
import { LoadingOverlay } from "@/components/LoadingOverlay";
import { api } from "@/lib/api";
import { Campaign, MetricSnapshot, Variant } from "@/lib/types";

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

export default function ComparePage() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const localStateKey = `launchpad-compare-state-${id}`;
  const [campaign, setCampaign] = useState<Campaign | null>(null);
  const [variants, setVariants] = useState<Variant[]>([]);
  const [metrics, setMetrics] = useState<MetricSnapshot[]>([]);
  const [selectedVariantId, setSelectedVariantId] = useState<number | null>(null);
  const [goalPrompt, setGoalPrompt] = useState("Maximize conversion quality while keeping bounce under control.");
  const [advice, setAdvice] = useState<{ best_variant_id: number; best_variant_name?: string | null; confidence: number; rationale: string; next_step: string } | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [actionTick, setActionTick] = useState(0);
  const [simulationRuns, setSimulationRuns] = useState(20);
  const [optimizeResult, setOptimizeResult] = useState<{ variant_id: number; recommendation_id?: number } | null>(null);
  const [newVariantName, setNewVariantName] = useState("");
  const [compareError, setCompareError] = useState<string | null>(null);
  const [optimizedVariantId, setOptimizedVariantId] = useState<number | null>(null);
  const [optimizeSummary, setOptimizeSummary] = useState<{ target: string; rationale: string; hypothesis: string } | null>(null);
  const [simulationSummary, setSimulationSummary] = useState<string | null>(null);
  const [adviceJobId, setAdviceJobId] = useState<string | null>(null);
  const [adviceRunning, setAdviceRunning] = useState(false);
  const [adviceReady, setAdviceReady] = useState(false);
  const [adviceNotice, setAdviceNotice] = useState<string | null>(null);
  const [showAdvicePanel, setShowAdvicePanel] = useState(true);
  const [optimizeJobId, setOptimizeJobId] = useState<string | null>(null);
  const [optimizeRunning, setOptimizeRunning] = useState(false);
  const [optimizationReady, setOptimizationReady] = useState(false);
  const [showOptimizationPanel, setShowOptimizationPanel] = useState(false);
  const [optimizeNotice, setOptimizeNotice] = useState<string | null>(null);
  const [dataSignature, setDataSignature] = useState("");
  const [adviceSignature, setAdviceSignature] = useState<string | null>(null);
  const [optimizationSignature, setOptimizationSignature] = useState<string | null>(null);

  async function refresh(
    _preferredVariantId?: number,
    _preferredRecommendationId?: number,
    ensureCoverage: boolean = true
  ) {
    const [c, v, m] = await Promise.all([
      api.getCampaign(id),
      api.listVariants(id),
      api.listMetrics(id)
    ]);
    let nextMetrics = m;
    const metricVariantIds = new Set(m.map((item) => item.variant_id));
    const hasMissingVariantMetrics = v.some((item) => !metricVariantIds.has(item.id));
    if (ensureCoverage && hasMissingVariantMetrics) {
      for (let i = 0; i < 3; i++) {
        await api.simulateBatch(id);
      }
      nextMetrics = await api.listMetrics(id);
    }
    const baselineId = Number(c.constraints_json?.baseline_variant_id || 0) || null;
    setCampaign(c);
    setVariants(v);
    setMetrics(nextMetrics);
    const variantPart = v.map((item) => item.id).sort((a, b) => a - b).join(",");
    setDataSignature(`${variantPart}|${nextMetrics.length}`);
    if (advice && !v.some((item) => item.id === advice.best_variant_id)) {
      setAdvice(null);
      setShowAdvicePanel(false);
      setAdviceNotice(null);
      setAdviceReady(false);
      setAdviceSignature(null);
    }
    if (optimizeResult && !v.some((item) => item.id === optimizeResult.variant_id)) {
      setOptimizeResult(null);
      setOptimizeSummary(null);
      setOptimizedVariantId(null);
      setShowOptimizationPanel(false);
      setOptimizeNotice(null);
      setOptimizationReady(false);
      setOptimizationSignature(null);
    }
    if (!selectedVariantId && v.length) {
      setSelectedVariantId(baselineId && v.some((item) => item.id === baselineId) ? baselineId : v[0].id);
    }
    return { metricCount: nextMetrics.length, variantCount: v.length };
  }

  useEffect(() => {
    if (!Number.isNaN(id)) refresh();
  }, [id]);

  useEffect(() => {
    if (typeof window === "undefined" || Number.isNaN(id)) return;
    const raw = window.localStorage.getItem(localStateKey);
    if (!raw) return;
    try {
      const parsed = JSON.parse(raw);
      if (typeof parsed.goalPrompt === "string") setGoalPrompt(parsed.goalPrompt);
      if (parsed.advice && typeof parsed.advice.best_variant_id === "number") {
        setAdvice(parsed.advice);
        setShowAdvicePanel(Boolean(parsed.showAdvicePanel ?? true));
        setAdviceReady(Boolean(parsed.adviceReady ?? false));
        setAdviceNotice(typeof parsed.adviceNotice === "string" ? parsed.adviceNotice : null);
        setAdviceSignature(typeof parsed.adviceSignature === "string" ? parsed.adviceSignature : null);
      }
      if (parsed.optimizeResult && typeof parsed.optimizeResult.variant_id === "number") {
        setOptimizeResult(parsed.optimizeResult);
        setOptimizeSummary(parsed.optimizeSummary || null);
        setNewVariantName(parsed.newVariantName || "");
        setOptimizedVariantId(parsed.optimizedVariantId || null);
        setShowOptimizationPanel(Boolean(parsed.showOptimizationPanel ?? false));
        setOptimizationReady(Boolean(parsed.optimizationReady ?? false));
        setOptimizeNotice(typeof parsed.optimizeNotice === "string" ? parsed.optimizeNotice : null);
        setOptimizationSignature(typeof parsed.optimizationSignature === "string" ? parsed.optimizationSignature : null);
      }
      if (typeof parsed.adviceJobId === "string" && parsed.adviceJobId) {
        setAdviceJobId(parsed.adviceJobId);
        setAdviceRunning(Boolean(parsed.adviceRunning));
      }
      if (typeof parsed.optimizeJobId === "string" && parsed.optimizeJobId) {
        setOptimizeJobId(parsed.optimizeJobId);
        setOptimizeRunning(Boolean(parsed.optimizeRunning));
      }
      if (parsed.advice && parsed.showAdvicePanel === false && parsed.adviceReady !== true) {
        setAdviceReady(true);
        setAdviceNotice("Best-variant analysis is ready. Click 'Reveal Recommendation'.");
      }
      if (parsed.optimizeResult && parsed.showOptimizationPanel === false && parsed.optimizationReady !== true) {
        setOptimizationReady(true);
        setOptimizeNotice("Optimization is ready. Click 'Reveal Optimization' to review and save it.");
      }
    } catch {
      // Ignore malformed local cache.
    }
  }, [id, localStateKey]);

  useEffect(() => {
    if (!dataSignature) return;
    if (advice && adviceSignature && adviceSignature !== dataSignature) {
      setAdvice(null);
      setAdviceReady(false);
      setAdviceNotice(null);
      setShowAdvicePanel(false);
      setAdviceSignature(null);
    }
    if (optimizeResult && optimizationSignature && optimizationSignature !== dataSignature) {
      setOptimizeResult(null);
      setOptimizeSummary(null);
      setOptimizedVariantId(null);
      setOptimizationReady(false);
      setOptimizeNotice(null);
      setShowOptimizationPanel(false);
      setOptimizationSignature(null);
    }
  }, [dataSignature, advice, adviceSignature, optimizeResult, optimizationSignature]);

  useEffect(() => {
    if (typeof window === "undefined" || Number.isNaN(id)) return;
    window.localStorage.setItem(
      localStateKey,
      JSON.stringify({
        goalPrompt,
        advice,
        adviceReady,
        adviceNotice,
        adviceSignature,
        showAdvicePanel,
        optimizeResult,
        optimizeSummary,
        newVariantName,
        optimizedVariantId,
        optimizationReady,
        optimizeNotice,
        optimizationSignature,
        showOptimizationPanel,
        adviceJobId,
        adviceRunning,
        optimizeJobId,
        optimizeRunning,
      })
    );
  }, [
    id,
    localStateKey,
    goalPrompt,
    advice,
    adviceReady,
    adviceNotice,
    adviceSignature,
    showAdvicePanel,
    optimizeResult,
    optimizeSummary,
    newVariantName,
    optimizedVariantId,
    optimizationReady,
    optimizeNotice,
    optimizationSignature,
    showOptimizationPanel,
    adviceJobId,
    adviceRunning,
    optimizeJobId,
    optimizeRunning,
  ]);

  useEffect(() => {
    if (!adviceJobId) return;
    let cancelled = false;
    const interval = setInterval(async () => {
      try {
        const status = await api.getAdviseVariantsJob(id, adviceJobId);
        if (cancelled) return;
        if (status.status === "SUCCEEDED") {
          clearInterval(interval);
          setAdviceRunning(false);
          setAdviceJobId(null);
          if (status.result) {
            setAdvice(status.result);
            setSelectedVariantId(status.result.best_variant_id);
          }
          setAdviceReady(true);
          setAdviceSignature(dataSignature || null);
          setAdviceNotice("Best-variant analysis is ready. Click 'Reveal Recommendation'.");
          setShowAdvicePanel(false);
          setActionTick((v) => v + 1);
        } else if (status.status === "FAILED") {
          clearInterval(interval);
          setAdviceRunning(false);
          setAdviceJobId(null);
          setAdviceNotice(null);
          setCompareError(status.error || "Best-variant analysis failed.");
        }
      } catch {
        if (!cancelled) {
          clearInterval(interval);
          setAdviceRunning(false);
          setAdviceJobId(null);
          setCompareError("Unable to poll best-variant analysis status.");
        }
      }
    }, 2000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [id, adviceJobId, dataSignature]);

  useEffect(() => {
    if (!optimizeJobId) return;
    let cancelled = false;
    const interval = setInterval(async () => {
      try {
        const status = await api.getAutoOptimizeJob(id, optimizeJobId);
        if (cancelled) return;
        if (status.status === "SUCCEEDED") {
          clearInterval(interval);
          setOptimizeRunning(false);
          setOptimizeJobId(null);
          const result = status.result || {};
          setOptimizeResult({ variant_id: result.variant_id, recommendation_id: result.applied_recommendation_id });
          const recommendations = await api.listRecommendations(id);
          const applied = recommendations.find((item: any) => item.id === result.applied_recommendation_id);
          setOptimizeSummary(
            applied
              ? {
                  target: applied.target_component,
                  rationale: applied.rationale,
                  hypothesis: applied.hypothesis,
                }
              : null
          );
          setOptimizationReady(true);
          setOptimizationSignature(dataSignature || null);
          setOptimizeNotice("Optimization is ready. Click 'Reveal Optimization' to review and save it.");
          const candidateName = `Variant ${String.fromCharCode(65 + Math.min(variants.length, 25))}`;
          setNewVariantName(candidateName);
          setOptimizedVariantId(null);
          setCompareError(null);
          await refresh();
          setActionTick((v) => v + 1);
        } else if (status.status === "FAILED") {
          clearInterval(interval);
          setOptimizeRunning(false);
          setOptimizeJobId(null);
          setOptimizeNotice(null);
          setCompareError(status.error || "Auto-optimization failed.");
        }
      } catch {
        if (!cancelled) {
          clearInterval(interval);
          setOptimizeRunning(false);
          setOptimizeJobId(null);
          setCompareError("Unable to poll optimization status.");
        }
      }
    }, 2000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [id, optimizeJobId, variants.length, dataSignature]);

  if (!campaign) return <div className="rounded-xl border bg-white p-6 text-sm text-slate-500">Loading compare studio...</div>;
  const baselineVariantId = Number(campaign.constraints_json?.baseline_variant_id || 0) || null;
  const variantLabel = (variantId: number | null | undefined) => {
    if (!variantId) return "";
    const found = variants.find((item) => item.id === variantId);
    if (!found) return `Variant ${variantId}`;
    if (variantId === baselineVariantId) return "Baseline";
    return found.name;
  };
  const humanizeOptimizationNarrative = (text: string) => {
    let output = text || "";
    output = output.replace(/\b[Vv]ariant\s*#?\s*(\d+)\b/g, (_match, idText) => {
      const idNumber = Number(idText);
      return variantLabel(Number.isNaN(idNumber) ? null : idNumber);
    });
    const pathTokens = [
      "hero.headline",
      "hero.subheadline",
      "hero.cta_text",
      "hero.trust_callout",
      "banner.text",
      "banner.badge",
      "bullets.0",
      "bullets.1",
      "bullets.2",
      "meta.rationale",
      "product image block",
    ];
    for (const token of pathTokens) {
      const escaped = token.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      output = output.replace(new RegExp(escaped, "gi"), humanLabel(token));
    }
    return output;
  };

  return (
    <div className="space-y-4">
      <LoadingOverlay
        show={!!busy}
        message={
          busy === "simulate"
            ? "Running simulation and refreshing KPI trends..."
            : busy === "advise"
              ? "Codex is analyzing variants..."
              : "Working..."
        }
      />
      <div className="flex items-center justify-between rounded-2xl border border-slate-200/70 bg-white/75 p-4 shadow-[0_10px_30px_rgba(15,23,42,0.06)] backdrop-blur">
        <div>
          <p className="text-xs uppercase text-slate-500">Compare Studio</p>
          <h1 className="text-2xl font-semibold text-slate-900">{campaign.name}</h1>
        </div>
        <div className="flex gap-2">
          <Link href="/campaigns" className="rounded border bg-white px-3 py-2 text-sm">Campaigns</Link>
          <Link href={`/campaigns/${id}/build`} className="rounded border bg-white px-3 py-2 text-sm">Build</Link>
        </div>
      </div>
      <IdlePrompt
        active={!busy}
        actionTick={actionTick}
        tips={[
          "Start with 'Run Simulation' to refresh KPI results across your saved variants.",
          "Use the compare assistant in plain language to identify the strongest variant for your goal.",
          "Run 'Auto-Optimize Best Variant' after advice to apply one guided improvement."
        ]}
      />

      <div className="rounded-2xl border border-slate-200/80 bg-white/85 p-4 shadow-[0_8px_28px_rgba(15,23,42,0.05)] backdrop-blur">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-sm font-semibold text-slate-900">Variant KPI Compare</p>
          <div className="flex gap-2">
            <label className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-2 py-2 text-xs text-slate-700">
              Simulation batches
              <input
                className="w-24"
                type="range"
                min={10}
                max={100}
                step={10}
                value={simulationRuns}
                onChange={(e) => setSimulationRuns(Number(e.target.value))}
              />
              <span className="w-8 text-right">{simulationRuns}</span>
            </label>
            <button
              className="rounded-lg bg-slate-900 px-3 py-2 text-sm text-white"
              onClick={async () => {
                setBusy("simulate");
                setSimulationSummary(null);
                try {
                  const beforeCount = metrics.length;
                  for (let i = 0; i < simulationRuns; i++) {
                    await api.simulateBatch(id);
                  }
                  const refreshed = await refresh(undefined, undefined, false);
                  const variantCount = refreshed?.variantCount || variants.length;
                  const expectedTotal = simulationRuns * variantCount;
                  setSimulationSummary(
                    `Ran ${simulationRuns} simulation batches. Added ${simulationRuns} new snapshots per variant (${expectedTotal} total across ${variantCount} variants).`
                  );
                  setActionTick((v) => v + 1);
                } finally {
                  setBusy(null);
                }
              }}
            >
              Run Simulation
            </button>
          </div>
        </div>
        {simulationSummary ? (
          <p className="mt-2 rounded border border-emerald-200 bg-emerald-50 px-2 py-1 text-xs text-emerald-800">{simulationSummary}</p>
        ) : null}
        <div className="mt-3">
          <KPICharts
            metrics={metrics}
            variantLabels={Object.fromEntries(
              variants.map((v) => [
                v.id,
                v.id === (Number(campaign.constraints_json?.baseline_variant_id || 0) || null) ? "Baseline" : v.name,
              ])
            )}
            baselineVariantId={Number(campaign.constraints_json?.baseline_variant_id || 0) || null}
          />
        </div>
      </div>

      <div className="rounded-2xl border border-slate-200/80 bg-white/85 p-4 shadow-[0_8px_28px_rgba(15,23,42,0.05)] backdrop-blur">
        <p className="text-sm font-semibold text-slate-900">Codex Compare Assistant</p>
        <p className="text-xs text-slate-600">Use natural language to choose the best variant and optionally auto-optimize it.</p>
        <textarea className="mt-2 w-full rounded-lg border border-slate-200 p-2 text-sm" rows={2} value={goalPrompt} onChange={(e) => setGoalPrompt(e.target.value)} />
        <div className="mt-2 flex flex-wrap gap-2">
          <button
            className="rounded-lg bg-indigo-700 px-3 py-2 text-xs text-white disabled:opacity-60"
            disabled={!!busy || adviceRunning}
            onClick={async () => {
              setCompareError(null);
              setAdviceReady(false);
              setShowAdvicePanel(false);
              setAdviceNotice("Codex best-variant analysis started. You can keep working while it runs.");
              const variantIds = variants.map((v) => v.id);
              const started = await api.startAdviseVariantsJob(id, { user_goal: goalPrompt, variant_ids: variantIds });
              setAdviceJobId(started.job_id);
              setAdviceRunning(true);
            }}
          >
            {adviceRunning ? "Analysis Running..." : "Ask Codex Which Variant Is Best"}
          </button>
          <button
            className="rounded-lg bg-emerald-700 px-3 py-2 text-xs text-white disabled:opacity-60"
            disabled={!!busy || optimizeRunning}
            onClick={async () => {
              setCompareError(null);
              setOptimizeResult(null);
              setOptimizeSummary(null);
              setOptimizedVariantId(null);
              setNewVariantName("");
              setOptimizationReady(false);
              setOptimizationSignature(null);
              setShowOptimizationPanel(false);
              setOptimizeNotice("Codex auto-optimization started. You can continue working while it runs.");
              try {
                const started = await api.startAutoOptimizeJob(id, {
                  user_goal: goalPrompt,
                  preferred_variant_id: advice?.best_variant_id || selectedVariantId || undefined,
                });
                setOptimizeJobId(started.job_id);
                setOptimizeRunning(true);
              } finally {
                // no-op: optimization runs in background
              }
            }}
          >
            {optimizeRunning ? "Optimization Running..." : "Auto-Optimize Best Variant"}
          </button>
        </div>
        {adviceNotice ? (
          <div className="mt-2 rounded border border-indigo-200 bg-indigo-50 px-2 py-2 text-xs text-indigo-800">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span>{adviceNotice}</span>
              {adviceReady ? (
                <button
                  className="rounded border border-indigo-300 bg-white px-2 py-1 text-xs text-indigo-700"
                  onClick={() => {
                    setShowAdvicePanel(true);
                    setAdviceNotice(null);
                  }}
                >
                  Reveal Recommendation
                </button>
              ) : (
                <button
                  className="rounded border border-indigo-300 bg-white px-2 py-1 text-xs text-indigo-700"
                  onClick={() => setAdviceNotice(null)}
                >
                  Dismiss
                </button>
              )}
            </div>
          </div>
        ) : null}
        {optimizeNotice ? (
          <div className="mt-2 rounded border border-indigo-200 bg-indigo-50 px-2 py-2 text-xs text-indigo-800">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span>{optimizeNotice}</span>
              {optimizationReady ? (
                <div className="flex items-center gap-2">
                  <button
                    className="rounded border border-indigo-300 bg-white px-2 py-1 text-xs text-indigo-700"
                    onClick={() => {
                      setShowOptimizationPanel(true);
                      setOptimizeNotice(null);
                    }}
                  >
                    Reveal Optimization
                  </button>
                  <Link
                    href={`/campaigns/${id}/build${optimizeResult?.variant_id ? `?variantId=${optimizeResult.variant_id}` : ""}`}
                    className="rounded border border-indigo-300 bg-white px-2 py-1 text-xs text-indigo-700"
                  >
                    Go To Build
                  </Link>
                </div>
              ) : (
                <button
                  className="rounded border border-indigo-300 bg-white px-2 py-1 text-xs text-indigo-700"
                  onClick={() => setOptimizeNotice(null)}
                >
                  Dismiss
                </button>
              )}
            </div>
          </div>
        ) : null}
        {advice && showAdvicePanel ? (
          <div className="mt-3 rounded border bg-slate-50 p-3 text-sm">
            <p className="font-semibold">Recommended Variant: {advice.best_variant_name || variantLabel(advice.best_variant_id)}</p>
            <p className="text-slate-700">{advice.rationale}</p>
            <p className="text-xs text-slate-600">Confidence {(advice.confidence * 100).toFixed(0)}% · Next: {advice.next_step}</p>
            <p className="mt-2 text-xs text-slate-700">
              Strategy note: if Variant A wins CTR and Variant B wins add-to-cart, run the next A/B test with one controlled change borrowed from B into A.
            </p>
            <div className="mt-2">
              <Link href={`/campaigns/${id}/build?variantId=${advice.best_variant_id}`} className="rounded border bg-white px-3 py-2 text-xs">
                Open Recommended Variant In Build
              </Link>
            </div>
          </div>
        ) : null}
        {optimizeResult && showOptimizationPanel && !optimizeRunning ? (
          <div className="mt-3 rounded border border-emerald-200 bg-emerald-50 p-3 text-sm">
            <p className="font-semibold text-emerald-900">Optimization applied to {variantLabel(optimizeResult.variant_id)}</p>
            {optimizeSummary ? (
              <div className="mt-1 rounded border border-emerald-300 bg-white/60 p-2 text-xs text-emerald-900">
                <p><span className="font-semibold">Changed area:</span> {humanLabel(optimizeSummary.target)}</p>
                <p><span className="font-semibold">Why:</span> {humanizeOptimizationNarrative(optimizeSummary.rationale)}</p>
                <p><span className="font-semibold">Expected effect:</span> {humanizeOptimizationNarrative(optimizeSummary.hypothesis)}</p>
              </div>
            ) : null}
            <p className="mt-2 text-emerald-800">Name this optimized variant (required), then open it in Build.</p>
            <input
              className="mt-2 w-full rounded border border-emerald-300 bg-white px-2 py-2 text-sm"
              placeholder="New variant name (required)"
              value={newVariantName}
              onChange={(e) => {
                setNewVariantName(e.target.value);
                setCompareError(null);
              }}
            />
            <div className="mt-2 flex flex-wrap gap-2">
              <button
                className="rounded bg-emerald-700 px-3 py-2 text-xs text-white disabled:opacity-50"
                disabled={!newVariantName.trim() || !optimizeResult.recommendation_id}
                onClick={async () => {
                  if (!optimizeResult.recommendation_id) return;
                  const normalized = newVariantName.trim().toLowerCase();
                  if (variants.some((variant) => variant.name.trim().toLowerCase() === normalized)) {
                    setCompareError("Variant name already exists. Please choose a unique name.");
                    return;
                  }
                  setBusy("save");
                  try {
                    const createdVariant = await api.saveRecommendationVariant(
                      optimizeResult.recommendation_id,
                      { variant_name: newVariantName.trim() }
                    );
                    setOptimizedVariantId(createdVariant.id);
                    await refresh();
                    setActionTick((v) => v + 1);
                    setShowOptimizationPanel(false);
                    setOptimizationReady(false);
                    setOptimizeNotice(null);
                  } finally {
                    setBusy(null);
                  }
                }}
              >
                Save Optimized As New Variant
              </button>
              <Link
                href={`/campaigns/${id}/build${optimizedVariantId ? `?variantId=${optimizedVariantId}` : ""}`}
                className="rounded border bg-white px-3 py-2 text-xs"
              >
                Open In Build
              </Link>
            </div>
            {compareError ? <p className="mt-2 rounded border border-rose-200 bg-rose-50 px-2 py-1 text-xs text-rose-700">{compareError}</p> : null}
          </div>
        ) : null}
      </div>
    </div>
  );
}
