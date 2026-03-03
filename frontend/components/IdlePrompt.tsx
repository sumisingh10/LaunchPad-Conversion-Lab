"use client";

/**
 * Module overview for frontend/components/IdlePrompt.tsx.
 * Implements user-facing UI behavior for this route or component.
 */

import { useEffect, useMemo, useState } from "react";

export function IdlePrompt({
  active,
  tips,
  actionTick
}: {
  active: boolean;
  tips: string[];
  actionTick: number;
}) {
  const [visible, setVisible] = useState(false);
  const [index, setIndex] = useState(0);

  useEffect(() => {
    if (!active || tips.length === 0) {
      setVisible(false);
      return;
    }
    setVisible(false);
    const timer = setTimeout(() => setVisible(true), 18000);
    return () => clearTimeout(timer);
  }, [active, actionTick, tips.length]);

  useEffect(() => {
    if (!visible || tips.length < 2) return;
    const rotate = setInterval(() => setIndex((i) => (i + 1) % tips.length), 9000);
    return () => clearInterval(rotate);
  }, [visible, tips.length]);

  const message = useMemo(() => tips[index] || "", [tips, index]);

  if (!visible || !message) return null;

  return (
    <div className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">
      Helpful tip: {message}
    </div>
  );
}
