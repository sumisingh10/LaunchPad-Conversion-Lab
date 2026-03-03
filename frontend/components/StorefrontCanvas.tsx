/**
 * Module overview for frontend/components/StorefrontCanvas.tsx.
 * Contains runtime logic for this feature area in LaunchPad Conversion Lab.
 */
import { Variant } from "@/lib/types";

function ring(on: boolean) {
  return on ? "ring-2 ring-emerald-400 outline outline-1 outline-emerald-300" : "";
}

export function StorefrontCanvas({
  variant,
  highlightPath,
  onSelectArea,
}: {
  variant: Variant | null;
  highlightPath?: string | null;
  onSelectArea?: (path: string) => void;
}) {
  if (!variant) {
    return <div className="rounded-2xl border bg-white p-8 text-sm text-slate-500">Generate or select a variant to render storefront.</div>;
  }
  const a = variant.assets_json;
  const selectArea = (path: string) => () => onSelectArea?.(path);
  const normalizedHighlight = String(highlightPath || "").toLowerCase().replace(/[._]/g, " ").trim();
  const matches = (tokens: string[]) => tokens.some((token) => normalizedHighlight.includes(token));
  const layoutHighlight = matches(["image", "layout", "grid", "product image block"]);
  const layoutMode = String(a?.meta?.rationale || "").includes("layout:image-first")
    ? "image-first"
    : String(a?.meta?.rationale || "").includes("layout:image-stack")
      ? "image-stack"
      : "text-first";
  const imageFirst = layoutMode === "image-first";
  const stackFirst = layoutMode === "image-stack";

  const imageGrid = (
    <button type="button" className={`grid grid-cols-2 gap-2 text-left ${ring(layoutHighlight)}`} onClick={selectArea("product image block")}>
      <div className="h-40 rounded bg-[linear-gradient(120deg,#f4f4f5,#d4d4d8)]" />
      <div className="h-40 rounded bg-[linear-gradient(120deg,#e5e7eb,#f8fafc)]" />
      <div className="h-40 rounded bg-[linear-gradient(120deg,#f8fafc,#e2e8f0)]" />
      <div className="h-40 rounded bg-[linear-gradient(120deg,#e2e8f0,#f8fafc)]" />
    </button>
  );

  const imageStack = (
    <button type="button" className={`grid grid-cols-1 gap-2 text-left ${ring(layoutHighlight)}`} onClick={selectArea("product image block")}>
      <div className="h-24 rounded bg-[linear-gradient(120deg,#f4f4f5,#d4d4d8)]" />
      <div className="h-24 rounded bg-[linear-gradient(120deg,#e5e7eb,#f8fafc)]" />
      <div className="h-24 rounded bg-[linear-gradient(120deg,#f8fafc,#e2e8f0)]" />
      <div className="h-24 rounded bg-[linear-gradient(120deg,#e2e8f0,#f8fafc)]" />
    </button>
  );

  const heroPanel = (
    <div className="space-y-4">
      <button type="button" className={`w-full text-left text-4xl font-semibold text-slate-900 ${ring(matches(["headline"]) && !matches(["subheadline"]))}`} onClick={selectArea("hero.headline")}>
        {a.hero.headline}
      </button>
      <button type="button" className={`w-full text-left text-slate-600 ${ring(matches(["subheadline"]))}`} onClick={selectArea("hero.subheadline")}>
        {a.hero.subheadline}
      </button>
      <div className="flex items-center gap-3">
        <button type="button" onClick={selectArea("hero.cta_text")} className={`rounded bg-black px-4 py-2 text-sm font-semibold text-white ${ring(matches(["cta", "click-through action", "button"]))}`}>
          {a.hero.cta_text}
        </button>
        <button type="button" onClick={selectArea("hero.trust_callout")} className={`text-left text-xs text-slate-500 ${ring(matches(["trust", "callout", "shipping", "warranty"]))}`}>
          {a.hero.trust_callout}
        </button>
      </div>
      <ul className={`grid gap-2 md:grid-cols-3 ${ring(matches(["bullet"]))}`}>
        {a.bullets.map((b: string, i: number) => (
          <li key={i}>
            <button
              type="button"
              onClick={selectArea("bullets")}
              className="w-full rounded bg-slate-100 px-3 py-2 text-left text-sm text-slate-700"
            >
              {b}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
  return (
    <div className="overflow-hidden rounded-2xl border bg-white shadow-sm">
      <div className="grid grid-cols-2 gap-4 bg-black/95 p-3 text-xs uppercase tracking-wide text-white md:grid-cols-5">
        <span>Women</span>
        <span>Men</span>
        <span>Bags</span>
        <span>Accessories</span>
        <span>New Arrivals</span>
      </div>
      <button
        type="button"
        className={`w-full bg-stone-100 px-5 py-3 text-left text-sm text-stone-700 ${ring(matches(["banner", "promo"]))}`}
        onClick={selectArea("banner.text")}
      >
        {a.banner.text}
      </button>
      {stackFirst ? (
        <div className="grid gap-6 p-6 lg:grid-cols-[0.9fr_1.3fr]">
          {imageStack}
          {heroPanel}
        </div>
      ) : (
        <div className={`grid gap-6 p-6 ${imageFirst ? "lg:grid-cols-[1fr_1.2fr]" : "lg:grid-cols-[1.2fr_1fr]"}`}>
          {imageFirst ? imageGrid : null}
          {heroPanel}
          {!imageFirst ? imageGrid : null}
        </div>
      )}
    </div>
  );
}
