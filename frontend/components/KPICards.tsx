/**
 * Module overview for frontend/components/KPICards.tsx.
 * Contains runtime logic for this feature area in LaunchPad Conversion Lab.
 */
import { MetricSnapshot } from "@/lib/types";

export function KPICards({ metrics }: { metrics: MetricSnapshot[] }) {
  return (
    <div className="grid gap-3 md:grid-cols-3">
      {metrics.map((m) => (
        <div key={m.id} className="rounded-lg border bg-white p-4">
          <p className="text-sm text-slate-500">Variant #{m.variant_id}</p>
          <p className="text-sm">CTR: {(m.ctr * 100).toFixed(2)}%</p>
          <p className="text-sm">ATC: {(m.atc_rate * 100).toFixed(2)}%</p>
          <p className="text-sm">Bounce: {(m.bounce_rate * 100).toFixed(2)}%</p>
        </div>
      ))}
    </div>
  );
}
