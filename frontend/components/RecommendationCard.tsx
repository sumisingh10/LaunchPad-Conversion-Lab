/**
 * Module overview for frontend/components/RecommendationCard.tsx.
 * Contains runtime logic for this feature area in LaunchPad Conversion Lab.
 */
import { Recommendation } from "@/lib/types";

function humanPath(path: string): string {
  return path
    .replace(/\./g, " > ")
    .replace(/_/g, " ")
    .replace(/\bcta\b/gi, "CTA")
    .replace(/\bmeta\b/gi, "strategy");
}

function humanStatus(value: string): string {
  return value
    .replace(/_/g, " ")
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function humanType(value: string): string {
  return value
    .replace(/_/g, " ")
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export function RecommendationCard({
  recommendation,
  feedbackSummary,
  onApprove,
  onReject,
  onApply,
  onFeedback,
  onPreview
}: {
  recommendation: Recommendation;
  feedbackSummary?: { positive_count: number; negative_count: number; avg_rating: number | null };
  onApprove: (id: number) => Promise<void>;
  onReject: (id: number) => Promise<void>;
  onApply: (id: number) => Promise<void>;
  onFeedback: (id: number, sentiment: "POSITIVE" | "NEGATIVE") => Promise<void>;
  onPreview: (id: number) => void;
}) {
  return (
    <div className="rounded-xl border bg-white p-4 shadow-sm">
      <div className="mb-2 flex items-center justify-between">
        <h4 className="font-semibold text-slate-900">
          #{recommendation.rank} {humanType(recommendation.change_type)}
        </h4>
        <span className="rounded-full bg-slate-100 px-2 py-1 text-xs text-slate-700">{humanStatus(recommendation.status)}</span>
      </div>
      <p className="text-sm">Target: {humanPath(recommendation.target_component)}</p>
      <p className="mt-1 text-sm text-slate-700">{recommendation.rationale}</p>
      <p className="mt-1 text-sm text-slate-500">Hypothesis: {recommendation.hypothesis}</p>
      <div className="mt-2 rounded bg-slate-50 p-2 text-xs text-slate-700">
        <p className="mb-1 font-semibold text-slate-900">Proposed edits</p>
        <ul className="space-y-1">
          {(recommendation.patch_json?.operations || []).map((op, idx) => (
            <li key={idx} className="rounded bg-white px-2 py-1">
              Update <span className="font-medium">{humanPath(op.path)}</span> to <span className="font-medium">"{String(op.value)}"</span>
            </li>
          ))}
        </ul>
      </div>
      {feedbackSummary ? (
        <p className="mt-2 text-xs text-slate-600">
          Sentiment: +{feedbackSummary.positive_count} / -{feedbackSummary.negative_count}
          {feedbackSummary.avg_rating !== null ? ` · avg rating ${feedbackSummary.avg_rating.toFixed(2)}` : ""}
        </p>
      ) : null}
      <div className="mt-3 flex gap-2">
        <button className="rounded bg-slate-700 px-2 py-1 text-white" onClick={() => onApprove(recommendation.id)}>
          Approve
        </button>
        <button className="rounded bg-rose-700 px-2 py-1 text-white" onClick={() => onReject(recommendation.id)}>
          Reject
        </button>
        <button className="rounded bg-accent px-2 py-1 text-white" onClick={() => onApply(recommendation.id)}>
          Apply
        </button>
        <button className="rounded bg-indigo-600 px-2 py-1 text-white" onClick={() => onPreview(recommendation.id)}>
          Preview Change
        </button>
        <button className="rounded bg-emerald-600 px-2 py-1 text-white" onClick={() => onFeedback(recommendation.id, "POSITIVE")}>
          Helpful 👍
        </button>
        <button className="rounded bg-orange-600 px-2 py-1 text-white" onClick={() => onFeedback(recommendation.id, "NEGATIVE")}>
          Not Helpful 👎
        </button>
      </div>
    </div>
  );
}
