"use client";

/**
 * Module overview for frontend/components/CampaignForm.tsx.
 * Implements user-facing UI behavior for this route or component.
 */

import { useState } from "react";

export function CampaignForm({ onSubmit }: { onSubmit: (payload: any) => Promise<void> }) {
  const [name, setName] = useState("");
  const [productTitle, setProductTitle] = useState("");
  const [category, setCategory] = useState("");
  const [segment, setSegment] = useState("");
  const [description, setDescription] = useState("");
  const [objective, setObjective] = useState("");
  const [busy, setBusy] = useState(false);
  const [missingFields, setMissingFields] = useState<string[]>([]);
  const [formError, setFormError] = useState<string | null>(null);

  const fieldError = (key: string) => missingFields.includes(key);
  const inputClass = (key: string) =>
    `rounded border p-2 ${fieldError(key) ? "border-rose-400 bg-rose-50" : ""}`;

  return (
    <form
      className="grid gap-3 rounded-xl border bg-white p-5 shadow-sm"
      onSubmit={async (e) => {
        e.preventDefault();
        const missing: string[] = [];
        if (!name.trim()) missing.push("name");
        if (!productTitle.trim()) missing.push("productTitle");
        if (!category.trim()) missing.push("category");
        if (!segment.trim()) missing.push("segment");
        if (!description.trim()) missing.push("description");
        if (missing.length) {
          setMissingFields(missing);
          setFormError("Please complete all required fields before creating a campaign.");
          return;
        }
        setMissingFields([]);
        setFormError(null);
        setBusy(true);
        try {
          await onSubmit({
            name,
            product_title: productTitle,
            product_category: category,
            product_description: description,
            objective: objective || "CTR",
            audience_segment: segment,
            constraints_json: {
              required_trust_phrase: "warranty"
            },
            primary_kpi: "CTR",
            status: "RUNNING"
          });
          setName("");
          setProductTitle("");
          setCategory("");
          setSegment("");
          setDescription("");
          setObjective("");
        } finally {
          setBusy(false);
        }
      }}
    >
      <h3 className="text-base font-semibold">Create Campaign</h3>
      {formError ? (
        <p className="rounded border border-rose-300 bg-rose-50 px-3 py-2 text-sm text-rose-700">{formError}</p>
      ) : null}
      <div className="grid gap-2 md:grid-cols-2">
        <input
          className={inputClass("name")}
          placeholder="Campaign name *"
          value={name}
          onChange={(e) => {
            setName(e.target.value);
            setMissingFields((prev) => prev.filter((item) => item !== "name"));
          }}
        />
        <input
          className={inputClass("productTitle")}
          placeholder="Product title *"
          value={productTitle}
          onChange={(e) => {
            setProductTitle(e.target.value);
            setMissingFields((prev) => prev.filter((item) => item !== "productTitle"));
          }}
        />
        <input
          className={inputClass("category")}
          placeholder="Category (e.g. Bags) *"
          value={category}
          onChange={(e) => {
            setCategory(e.target.value);
            setMissingFields((prev) => prev.filter((item) => item !== "category"));
          }}
        />
        <input
          className={inputClass("segment")}
          placeholder="Audience segment (e.g. Mobile first shoppers) *"
          value={segment}
          onChange={(e) => {
            setSegment(e.target.value);
            setMissingFields((prev) => prev.filter((item) => item !== "segment"));
          }}
        />
        <select
          className="rounded border p-2"
          value={objective}
          onChange={(e) => setObjective(e.target.value)}
        >
          <option value="">Objective (optional, default CTR)</option>
          <option value="CTR">Click-through Rate (CTR)</option>
          <option value="ATC">Add-to-cart Rate (ATC)</option>
          <option value="CONVERSION">Conversion</option>
        </select>
        <p className="md:col-span-2 -mt-1 text-xs text-slate-500">
          Note: Conversion is modeled from current funnel signals (ATC and bounce) in this MVP.
        </p>
      </div>
      <textarea
        className={`min-h-20 rounded border p-2 ${fieldError("description") ? "border-rose-400 bg-rose-50" : ""}`}
        placeholder="Brief product description for the landing page *"
        value={description}
        onChange={(e) => {
          setDescription(e.target.value);
          setMissingFields((prev) => prev.filter((item) => item !== "description"));
        }}
      />
      <button disabled={busy} className="rounded bg-accent px-3 py-2 text-white disabled:opacity-60">
        {busy ? "Creating..." : "Create"}
      </button>
    </form>
  );
}
