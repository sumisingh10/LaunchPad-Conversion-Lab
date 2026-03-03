/**
 * Module overview for frontend/components/PerformanceTrends.tsx.
 * Contains runtime logic for this feature area in LaunchPad Conversion Lab.
 */
import { FeedbackItem, LiftTraceEvent, MetricSnapshot } from "@/lib/types";

type Point = { x: number; y: number };

function line(points: Point[], width: number, height: number, minY: number, maxY: number) {
  if (!points.length) return "";
  return points
    .map((p, idx) => {
      const x = (p.x / Math.max(1, points.length - 1)) * width;
      const range = Math.max(1, maxY - minY);
      const y = height - ((p.y - minY) / range) * height;
      return `${idx === 0 ? "M" : "L"}${x},${y}`;
    })
    .join(" ");
}

function Chart({ title, points, color, suffix = "" }: { title: string; points: number[]; color: string; suffix?: string }) {
  const width = 300;
  const height = 90;
  const minY = Math.min(...points, 0);
  const maxY = Math.max(1, ...points);
  const path = line(points.map((y, x) => ({ x, y })), width, height, minY, maxY);
  const latest = points.length ? points[points.length - 1] : 0;
  return (
    <div className="rounded-xl border bg-white p-3">
      <div className="mb-2 flex items-center justify-between">
        <p className="text-sm font-semibold text-slate-800">{title}</p>
        <p className="text-xs text-slate-500">
          {latest.toFixed(2)}
          {suffix}
        </p>
      </div>
      <svg viewBox={`0 0 ${width} ${height}`} className="h-24 w-full rounded bg-slate-50">
        <path d={path} fill="none" stroke={color} strokeWidth="2" />
      </svg>
    </div>
  );
}

export function PerformanceTrends({
  metrics,
  feedback,
  trace
}: {
  metrics: MetricSnapshot[];
  feedback: FeedbackItem[];
  trace: LiftTraceEvent[];
}) {
  const snapshots = [...metrics].sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
  const revenueSeries = snapshots.map((m) => Number((m.add_to_cart * 80).toFixed(2)));

  const feedbackSorted = [...feedback].sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());
  let sentimentRunning = 0;
  const feedbackSentimentSeries = feedbackSorted.map((f) => {
    sentimentRunning += f.sentiment === "POSITIVE" ? 1 : -1;
    return sentimentRunning;
  });

  const traceSorted = [...trace].sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());
  let traceSentiment = 0;
  const traceSentimentSeries = traceSorted.map((t) => {
    if (t.event_type === "APPLIED") traceSentiment += 1;
    if (t.event_type === "REJECTED") traceSentiment -= 1;
    return traceSentiment;
  });
  const sentimentSeries = feedbackSentimentSeries.length ? feedbackSentimentSeries : traceSentimentSeries;
  let created = 0;
  let applied = 0;
  const recommendationSeries = traceSorted
    .filter((t) => t.event_type === "RECOMMENDATION_CREATED" || t.event_type === "APPLIED")
    .map((t) => {
      if (t.event_type === "RECOMMENDATION_CREATED") created += 1;
      if (t.event_type === "APPLIED") applied += 1;
      return created === 0 ? 0 : Number(((applied / created) * 100).toFixed(2));
    });

  return (
    <div className="grid gap-3 lg:grid-cols-3">
      <Chart title="Estimated Spend Over Time" points={revenueSeries} color="#0f766e" suffix=" USD" />
      <Chart title="User Sentiment Trend" points={sentimentSeries} color="#2563eb" />
      <Chart title="Recommendation Apply Rate" points={recommendationSeries} color="#7c3aed" suffix="%" />
    </div>
  );
}
