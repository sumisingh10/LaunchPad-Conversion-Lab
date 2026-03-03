"use client";

/**
 * Module overview for frontend/components/KPICharts.tsx.
 * Implements user-facing UI behavior for this route or component.
 */

import { useEffect, useMemo, useState } from "react";

import { MetricSnapshot } from "@/lib/types";

type MetricKey = "ctr" | "atc_rate" | "bounce_rate";
const METRIC_LABEL: Record<MetricKey, string> = {
  ctr: "Click-through Rate",
  atc_rate: "Add-to-cart Rate",
  bounce_rate: "Bounce Rate",
};

const COLORS = ["#0f766e", "#2563eb", "#7c3aed", "#ea580c", "#be123c", "#0891b2", "#0e7490", "#4f46e5"];

function uniqueIds(ids: number[]) {
  return Array.from(new Set(ids));
}

export function KPICharts({
  metrics,
  variantLabels = {},
  baselineVariantId,
}: {
  metrics: MetricSnapshot[];
  variantLabels?: Record<number, string>;
  baselineVariantId?: number | null;
}) {
  const [metric, setMetric] = useState<MetricKey>("ctr");
  const [deltaMetric, setDeltaMetric] = useState<MetricKey>("ctr");
  const [windowSize, setWindowSize] = useState<number>(50);
  const [xMetric, setXMetric] = useState<MetricKey>("ctr");
  const [yMetric, setYMetric] = useState<MetricKey>("atc_rate");

  const [trendVariantIds, setTrendVariantIds] = useState<number[]>([]);
  const [tradeoffVariantIds, setTradeoffVariantIds] = useState<number[]>([]);
  const [deltaVariantIds, setDeltaVariantIds] = useState<number[]>([]);

  const [trendPickId, setTrendPickId] = useState<number | "">("");
  const [tradeoffPickId, setTradeoffPickId] = useState<number | "">("");
  const [deltaPickId, setDeltaPickId] = useState<number | "">("");

  const byVariant = useMemo(() => {
    const map = new Map<number, MetricSnapshot[]>();
    for (const point of metrics) {
      if (!map.has(point.variant_id)) map.set(point.variant_id, []);
      map.get(point.variant_id)!.push(point);
    }
    for (const [id, points] of map.entries()) {
      map.set(id, [...points].sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()));
    }
    return map;
  }, [metrics]);

  const variants = Array.from(byVariant.entries()).sort((a, b) => {
    const aLabel = variantLabels[a[0]] || `Variant ${a[0]}`;
    const bLabel = variantLabels[b[0]] || `Variant ${b[0]}`;
    return aLabel.localeCompare(bLabel);
  });
  const allVariantIds = variants.map(([variantId]) => variantId);
  const totalSnapshots = metrics.length;
  const snapshotsPerVariant = variants.length ? Math.floor(totalSnapshots / variants.length) : totalSnapshots;
  const maxWindow = Math.max(5, snapshotsPerVariant);

  useEffect(() => {
    const ensureSelected = (current: number[]) => {
      const filtered = uniqueIds(current.filter((id) => allVariantIds.includes(id)));
      return filtered.length ? filtered : [...allVariantIds];
    };

    setTrendVariantIds((prev) => ensureSelected(prev));
    setTradeoffVariantIds((prev) => ensureSelected(prev));
    setDeltaVariantIds((prev) => ensureSelected(prev));
  }, [metrics.length, allVariantIds.join(",")]);

  useEffect(() => {
    setWindowSize((prev) => Math.min(Math.max(5, prev), maxWindow));
  }, [maxWindow]);

  if (!metrics.length) {
    return <div className="rounded-xl border bg-white p-6 text-sm text-slate-500">No KPI data yet. Simulate a batch to see trends.</div>;
  }

  const colorForVariant = (variantId: number) => COLORS[Math.max(0, allVariantIds.indexOf(variantId)) % COLORS.length];

  const activeTrendVariants = variants.filter(([id]) => trendVariantIds.includes(id));
  const activeTradeoffVariants = variants.filter(([id]) => tradeoffVariantIds.includes(id));
  const activeDeltaVariants = variants.filter(([id]) => deltaVariantIds.includes(id));

  const width = 720;
  const height = 220;
  const pad = 24;

  const visibleTrendSeries = activeTrendVariants.map(([variantId, points]) => [variantId, points.slice(-windowSize)] as const);
  const trendValues = visibleTrendSeries.flatMap(([, points]) => points.map((p) => p[metric]));
  const minY = Math.min(...(trendValues.length ? trendValues : [0]), 0);
  const maxY = Math.max(...(trendValues.length ? trendValues : [0.01]), 0.01);
  const yRange = Math.max(maxY - minY, 0.0001);

  const linePath = (points: MetricSnapshot[]) =>
    points
      .map((p, idx) => {
        const x = pad + (idx / Math.max(points.length - 1, 1)) * (width - pad * 2);
        const y = pad + (1 - (p[metric] - minY) / yRange) * (height - pad * 2);
        return `${idx === 0 ? "M" : "L"}${x},${y}`;
      })
      .join(" ");

  const latestForVariant = (variantId: number) => byVariant.get(variantId)?.slice(-1)[0];
  const previousForVariant = (variantId: number) => {
    const points = byVariant.get(variantId) || [];
    return points[Math.max(points.length - 2, 0)];
  };

  const scatterPoints = activeTradeoffVariants
    .map(([variantId]) => {
      const latest = latestForVariant(variantId);
      if (!latest) return null;
      return { variantId, x: latest[xMetric], y: latest[yMetric] };
    })
    .filter(Boolean) as Array<{ variantId: number; x: number; y: number }>;

  const xVals = scatterPoints.map((p) => p.x);
  const yVals = scatterPoints.map((p) => p.y);
  const minX = Math.min(...(xVals.length ? xVals : [0]), 0);
  const maxX = Math.max(...(xVals.length ? xVals : [0.01]), 0.01);
  const minSy = Math.min(...(yVals.length ? yVals : [0]), 0);
  const maxSy = Math.max(...(yVals.length ? yVals : [0.01]), 0.01);
  const sxRange = Math.max(maxX - minX, 0.0001);
  const syRange = Math.max(maxSy - minSy, 0.0001);

  const baselineLatest = baselineVariantId ? byVariant.get(baselineVariantId)?.slice(-1)[0] : undefined;
  const baselineMetric = baselineLatest ? baselineLatest[deltaMetric] : undefined;
  const deltaBars = activeDeltaVariants
    .map(([variantId]) => {
      const latest = latestForVariant(variantId);
      if (!latest) return null;
      const rawDelta = baselineMetric === undefined ? 0 : latest[deltaMetric] - baselineMetric;
      return { variantId, delta: rawDelta };
    })
    .filter(Boolean) as Array<{ variantId: number; delta: number }>;
  const maxDeltaAbs = Math.max(0.0001, ...deltaBars.map((item) => Math.abs(item.delta)));

  const renderSelector = (
    selectedIds: number[],
    setSelectedIds: (ids: number[]) => void,
    pickId: number | "",
    setPickId: (id: number | "") => void,
    options: { color?: boolean; label: string }
  ) => {
    const available = allVariantIds.filter((id) => !selectedIds.includes(id));
    return (
      <div className="mb-2 space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <select
            className="rounded border px-2 py-1 text-xs"
            value={pickId === "" ? "" : String(pickId)}
            onChange={(e) => setPickId(e.target.value ? Number(e.target.value) : "")}
          >
            <option value="">Select variant</option>
            {available.map((variantId) => (
              <option key={variantId} value={variantId}>
                {variantLabels[variantId] || `Variant ${variantId}`}
              </option>
            ))}
          </select>
          <button
            type="button"
            className="rounded border px-2 py-1 text-xs"
            onClick={() => {
              if (pickId === "") return;
              setSelectedIds(uniqueIds([...selectedIds, pickId]));
              setPickId("");
            }}
            disabled={pickId === ""}
          >
            Add
          </button>
        </div>
        <div className="flex flex-wrap gap-2 text-xs">
          {selectedIds.map((variantId) => (
            <span key={variantId} className="inline-flex items-center gap-1 rounded border bg-slate-50 px-2 py-1 text-slate-700">
              {options.color ? <span className="h-2 w-2 rounded-full" style={{ backgroundColor: colorForVariant(variantId) }} /> : null}
              {variantLabels[variantId] || `Variant ${variantId}`}
              <button
                type="button"
                className="ml-1 text-slate-400 hover:text-slate-700"
                onClick={() => {
                  if (selectedIds.length <= 1) return;
                  setSelectedIds(selectedIds.filter((id) => id !== variantId));
                }}
                title="Remove variant"
              >
                ×
              </button>
            </span>
          ))}
        </div>
        {options.color ? (
          <p className="text-xs text-slate-500">{options.label}: color legend updates as selected variants change.</p>
        ) : (
          <p className="text-xs text-slate-500">{options.label}</p>
        )}
      </div>
    );
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <label className="text-xs font-medium text-slate-600">Trend Metric</label>
        <select className="rounded border px-2 py-1 text-xs" value={metric} onChange={(e) => setMetric(e.target.value as MetricKey)}>
          <option value="ctr">Click-through Rate</option>
          <option value="atc_rate">Add-to-cart Rate</option>
          <option value="bounce_rate">Bounce Rate</option>
        </select>
        <label className="ml-2 text-xs font-medium text-slate-600">Most recent snapshots</label>
        <input
          type="range"
          min={5}
          max={maxWindow}
          value={Math.min(windowSize, maxWindow)}
          onChange={(e) => setWindowSize(Number(e.target.value))}
          className="w-32 accent-slate-800"
        />
        <input
          type="number"
          min={5}
          max={maxWindow}
          value={Math.min(windowSize, maxWindow)}
          onChange={(e) => {
            const next = Number(e.target.value || 0);
            if (Number.isNaN(next)) return;
            setWindowSize(Math.max(5, Math.min(maxWindow, next)));
          }}
          className="w-20 rounded border px-2 py-1 text-xs"
        />
        <span className="text-xs text-slate-500">
          Per-variant snapshots available: {snapshotsPerVariant} (total rows: {totalSnapshots})
        </span>
      </div>

      <div className="rounded-xl border bg-white p-3">
        {renderSelector(trendVariantIds, setTrendVariantIds, trendPickId, setTrendPickId, {
          color: true,
          label: "Trend legend",
        })}
        <svg viewBox={`0 0 ${width} ${height}`} className="h-64 w-full rounded bg-slate-50">
          {visibleTrendSeries.map(([variantId, points]) => (
            <path key={variantId} d={linePath(points)} fill="none" stroke={colorForVariant(variantId)} strokeWidth="2.5" />
          ))}
        </svg>
        <div className="mt-2 flex flex-wrap gap-3 text-xs">
          {activeTrendVariants.map(([variantId]) => {
            const latest = latestForVariant(variantId);
            const previous = previousForVariant(variantId);
            const momentum = previous && latest ? latest[metric] - previous[metric] : 0;
            return (
              <span key={variantId} className="inline-flex items-center gap-1 text-slate-700">
                <span className="h-2 w-2 rounded-full" style={{ backgroundColor: colorForVariant(variantId) }} />
                {variantLabels[variantId] || `Variant ${variantId}`}
                {latest ? ` · ${(latest[metric] * 100).toFixed(2)}%` : ""} {latest ? `(${momentum >= 0 ? "+" : ""}${(momentum * 100).toFixed(2)} pts)` : ""}
              </span>
            );
          })}
        </div>
      </div>

      <div className="rounded-xl border bg-white p-3">
        <div className="mb-2 flex flex-wrap items-center gap-2">
          <p className="text-sm font-semibold text-slate-900">KPI Trade-off View</p>
          <select className="rounded border px-2 py-1 text-xs" value={xMetric} onChange={(e) => setXMetric(e.target.value as MetricKey)}>
            <option value="ctr">X: Click-through Rate</option>
            <option value="atc_rate">X: Add-to-cart Rate</option>
            <option value="bounce_rate">X: Bounce Rate</option>
          </select>
          <select className="rounded border px-2 py-1 text-xs" value={yMetric} onChange={(e) => setYMetric(e.target.value as MetricKey)}>
            <option value="ctr">Y: Click-through Rate</option>
            <option value="atc_rate">Y: Add-to-cart Rate</option>
            <option value="bounce_rate">Y: Bounce Rate</option>
          </select>
        </div>
        {renderSelector(tradeoffVariantIds, setTradeoffVariantIds, tradeoffPickId, setTradeoffPickId, {
          color: true,
          label: "Trade-off legend",
        })}
        <svg viewBox={`0 0 ${width} ${height}`} className="h-64 w-full rounded bg-slate-50">
          {scatterPoints.map((point) => {
            const cx = pad + ((point.x - minX) / sxRange) * (width - pad * 2);
            const cy = pad + (1 - (point.y - minSy) / syRange) * (height - pad * 2);
            return <circle key={point.variantId} cx={cx} cy={cy} r={6} fill={colorForVariant(point.variantId)} />;
          })}
        </svg>
        <p className="mt-1 text-xs text-slate-500">
          X-axis: {METRIC_LABEL[xMetric]} · Y-axis: {METRIC_LABEL[yMetric]} (latest snapshot per variant)
        </p>
      </div>

      <div className="rounded-xl border bg-white p-3">
        <div className="mb-2 flex flex-wrap items-center gap-2">
          <p className="text-sm font-semibold text-slate-900">Delta vs Baseline ({METRIC_LABEL[deltaMetric]})</p>
          <select
            className="rounded border px-2 py-1 text-xs"
            value={deltaMetric}
            onChange={(e) => setDeltaMetric(e.target.value as MetricKey)}
          >
            <option value="ctr">Click-through Rate</option>
            <option value="atc_rate">Add-to-cart Rate</option>
            <option value="bounce_rate">Bounce Rate</option>
          </select>
        </div>
        {!baselineVariantId ? (
          <p className="text-xs text-slate-500">Set a baseline variant to enable delta comparison.</p>
        ) : (
          <div className="space-y-2">
            {renderSelector(deltaVariantIds, setDeltaVariantIds, deltaPickId, setDeltaPickId, {
              label: "Choose which variants appear in delta bars.",
            })}
            {deltaBars.map((item) => {
              const widthPct = `${(Math.abs(item.delta) / maxDeltaAbs) * 100}%`;
              const positive = item.delta >= 0;
              return (
                <div key={item.variantId} className="space-y-1">
                  <div className="flex items-center justify-between text-xs text-slate-700">
                    <span>{variantLabels[item.variantId] || `Variant ${item.variantId}`}</span>
                    <span>
                      {positive ? "+" : ""}
                      {(item.delta * 100).toFixed(2)} pts
                    </span>
                  </div>
                  <div className="h-2 rounded bg-slate-100">
                    <div className={`h-2 rounded ${positive ? "bg-emerald-500" : "bg-rose-500"}`} style={{ width: widthPct }} />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
