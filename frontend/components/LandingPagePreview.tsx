/**
 * Module overview for frontend/components/LandingPagePreview.tsx.
 * Contains runtime logic for this feature area in LaunchPad Conversion Lab.
 */
import { Variant } from "@/lib/types";

export function LandingPagePreview({
  title,
  variant,
  easyWins,
  highlightPath,
  snapshotUrl
}: {
  title: string;
  variant: Variant | null;
  easyWins: string[];
  highlightPath?: string | null;
  snapshotUrl?: string | null;
}) {
  if (!variant) {
    return <div className="rounded-xl border bg-white p-8 text-sm text-slate-500">Generate variants to preview a landing page.</div>;
  }

  const a = variant.assets_json;
  const highlights = {
    headline: highlightPath === "hero.headline",
    subheadline: highlightPath === "hero.subheadline",
    cta: highlightPath === "hero.cta_text",
    trust: highlightPath === "hero.trust_callout",
    bullets: String(highlightPath || "").startsWith("bullets"),
    banner: String(highlightPath || "").startsWith("banner")
  };
  return (
    <section className="overflow-hidden rounded-2xl border bg-white shadow-sm">
      <div className="bg-gradient-to-r from-slate-900 via-slate-800 to-teal-800 px-6 py-3 text-xs uppercase tracking-wide text-slate-200">
        Mock Landing Page Studio · {variant.name}
      </div>
      <div className="grid gap-6 p-6 lg:grid-cols-[1.4fr_1fr]">
        <div className="space-y-5">
          {snapshotUrl ? (
            <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
              <img src={snapshotUrl} alt="Landing page reference" className="h-48 w-full object-cover" />
              <p className="px-3 py-2 text-xs text-slate-500">Reference snapshot used for recommendation context</p>
            </div>
          ) : null}
          <div className="grid gap-4 rounded-2xl border border-slate-200 bg-gradient-to-br from-white to-slate-50 p-5 md:grid-cols-2">
            <div className="space-y-3">
              <div className="inline-flex rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-900">{a.banner.badge || "Offer"}</div>
              <h2 className={`rounded px-1 text-3xl font-semibold leading-tight text-slate-900 ${highlights.headline ? "ring-2 ring-indigo-400" : ""}`}>{a.hero.headline}</h2>
              <p className={`rounded px-1 text-sm text-slate-600 ${highlights.subheadline ? "ring-2 ring-indigo-400" : ""}`}>{a.hero.subheadline}</p>
              <button className={`rounded-lg px-4 py-2 text-sm font-semibold text-white ${highlights.cta ? "bg-indigo-600 ring-2 ring-indigo-300" : "bg-teal-700"}`}>{a.hero.cta_text}</button>
              <p className={`rounded px-1 text-xs text-slate-500 ${highlights.trust ? "ring-2 ring-indigo-400" : ""}`}>{a.hero.trust_callout}</p>
            </div>
            <div className="rounded-xl bg-slate-900 p-4 text-slate-100">
              <p className="text-xs uppercase tracking-wide text-slate-300">Product Visual</p>
              <div className="mt-3 grid grid-cols-2 gap-2">
                <div className="h-20 rounded bg-teal-700/60" />
                <div className="h-20 rounded bg-slate-700" />
                <div className="h-20 rounded bg-slate-700" />
                <div className="h-20 rounded bg-teal-600/70" />
              </div>
            </div>
          </div>
          <ul className={`grid gap-2 text-sm text-slate-700 md:grid-cols-3 ${highlights.bullets ? "rounded-lg ring-2 ring-indigo-300 p-1" : ""}`}>
            {a.bullets.map((b: string, i: number) => (
              <li key={i} className="rounded-md border bg-white px-3 py-2 shadow-sm">
                {b}
              </li>
            ))}
          </ul>
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-lg border bg-white p-3">
              <p className="text-xs uppercase text-slate-500">Hero Clarity</p>
              <p className="mt-1 text-sm font-semibold text-slate-800">High</p>
            </div>
            <div className="rounded-lg border bg-white p-3">
              <p className="text-xs uppercase text-slate-500">Trust Signal</p>
              <p className="mt-1 text-sm font-semibold text-slate-800">Tracked</p>
            </div>
            <div className="rounded-lg border bg-white p-3">
              <p className="text-xs uppercase text-slate-500">CTA Strength</p>
              <p className="mt-1 text-sm font-semibold text-slate-800">Review</p>
            </div>
          </div>
        </div>
        <div className="space-y-3">
          <div className={`rounded-xl border border-slate-200 bg-slate-50 p-4 ${highlights.banner ? "ring-2 ring-indigo-300" : ""}`}>
            <p className="text-xs font-semibold uppercase text-slate-500">Promo Strip</p>
            <p className="mt-2 rounded-lg bg-white p-3 text-sm text-slate-700">{a.banner.text}</p>
            <div className="mt-4 border-t pt-3 text-xs text-slate-500">
              <p>Campaign: {title}</p>
              <p>Strategy: {a.meta.strategy_tag}</p>
            </div>
          </div>
          <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4">
            <p className="text-xs font-semibold uppercase text-emerald-800">Easy Wins</p>
            {easyWins.length ? (
              <ul className="mt-2 space-y-2 text-sm text-emerald-900">
                {easyWins.map((tip, idx) => (
                  <li key={idx} className="rounded bg-white px-2 py-1">
                    {tip}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-2 text-xs text-emerald-800">No immediate low-risk edits detected. Use Propose Improvements for deeper changes.</p>
            )}
          </div>
          {highlightPath ? (
            <div className="rounded-xl border border-indigo-200 bg-indigo-50 p-3 text-xs text-indigo-900">
              Suggested change highlighted on page: <span className="font-semibold">{highlightPath}</span>
            </div>
          ) : null}
          <div className="rounded-xl border border-slate-200 bg-white p-4 text-xs text-slate-500">
            <p>Campaign: {title}</p>
            <p>Variant: {variant.name}</p>
            <p>Strategy: {a.meta.strategy_tag}</p>
          </div>
        </div>
      </div>
    </section>
  );
}
