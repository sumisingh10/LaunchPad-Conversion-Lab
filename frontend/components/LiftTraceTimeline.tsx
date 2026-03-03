/**
 * Module overview for frontend/components/LiftTraceTimeline.tsx.
 * Contains runtime logic for this feature area in LaunchPad Conversion Lab.
 */
import { LiftTraceEvent } from "@/lib/types";

function humanEvent(value: string): string {
  return value
    .replace(/_/g, " ")
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export function LiftTraceTimeline({ events }: { events: LiftTraceEvent[] }) {
  return (
    <div className="space-y-3">
      {events.map((event) => (
        <div key={event.id} className="rounded-lg border bg-white p-3">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-500">{humanEvent(event.event_type)}</span>
            <span className="text-xs text-slate-400">{new Date(event.created_at).toLocaleString()}</span>
          </div>
          <p className="text-sm">{event.summary}</p>
        </div>
      ))}
    </div>
  );
}
