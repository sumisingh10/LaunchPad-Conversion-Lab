/**
 * Module overview for frontend/components/VersionComparison.tsx.
 * Contains runtime logic for this feature area in LaunchPad Conversion Lab.
 */
import { OrgInsight, VariantVersionPerformance } from "@/lib/types";

function pct(v: number | null) {
  if (v == null) return "n/a";
  return `${(v * 100).toFixed(2)}%`;
}

export function VersionComparison({
  versions,
  orgInsights
}: {
  versions: VariantVersionPerformance[];
  orgInsights: OrgInsight[];
}) {
  return (
    <div className="grid gap-3 lg:grid-cols-2">
      <div className="rounded-xl border bg-white p-3">
        <p className="text-sm font-semibold text-slate-900">Latest 3 Version Comparison</p>
        <div className="mt-2 space-y-2">
          {versions.map((v) => (
            <div key={v.version_id} className="rounded border bg-slate-50 p-2 text-xs text-slate-700">
              <p className="font-semibold">Version {v.version_number}</p>
              <p>CTR {pct(v.avg_ctr)} · ATC {pct(v.avg_atc_rate)} · Bounce {pct(v.avg_bounce_rate)}</p>
              <p>Est. spend ${v.estimated_spend.toFixed(2)} · Sentiment score {v.sentiment_score ?? 0}</p>
            </div>
          ))}
        </div>
      </div>
      <div className="rounded-xl border bg-white p-3">
        <p className="text-sm font-semibold text-slate-900">Cross-Org Synthetic Benchmarks</p>
        <div className="mt-2 space-y-2">
          {orgInsights.slice(0, 3).map((i, idx) => (
            <div key={idx} className="rounded border bg-slate-50 p-2 text-xs text-slate-700">
              <p className="font-semibold">{i.change_type} · {i.segment}</p>
              <p>CTR +{i.avg_ctr_lift.toFixed(1)} pts · ATC +{i.avg_atc_lift.toFixed(1)} pts · Bounce {i.avg_bounce_delta.toFixed(1)} pts</p>
              <p>Sentiment +{i.avg_sentiment_delta.toFixed(1)} pts</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
