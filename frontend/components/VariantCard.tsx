/**
 * Module overview for frontend/components/VariantCard.tsx.
 * Contains runtime logic for this feature area in LaunchPad Conversion Lab.
 */
import { Variant } from "@/lib/types";

export function VariantCard({ variant }: { variant: Variant }) {
  const a = variant.assets_json;
  return (
    <div className="rounded-lg border bg-white p-4">
      <div className="mb-2 flex items-center justify-between">
        <h4 className="font-semibold">{variant.name}</h4>
        <span className="rounded bg-slate-100 px-2 py-1 text-xs">{variant.strategy_tag}</span>
      </div>
      <p className="font-medium">{a.hero.headline}</p>
      <p className="text-sm text-slate-600">{a.hero.subheadline}</p>
      <p className="mt-2 text-sm">CTA: {a.hero.cta_text}</p>
      <ul className="mt-2 list-disc pl-5 text-sm text-slate-700">
        {a.bullets.map((b: string, idx: number) => (
          <li key={idx}>{b}</li>
        ))}
      </ul>
    </div>
  );
}
