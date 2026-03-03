/**
 * Unit tests for RecommendationCard interaction wiring.
 * Verifies approve/reject/apply/preview/feedback handlers are invoked through user actions.
 */
import { fireEvent, render, screen } from "@testing-library/react";

import { RecommendationCard } from "@/components/RecommendationCard";

describe("RecommendationCard", () => {
  it("calls action handlers", async () => {
    const onApprove = vi.fn(async () => {});
    const onReject = vi.fn(async () => {});
    const onApply = vi.fn(async () => {});
    const onFeedback = vi.fn(async () => {});
    const onPreview = vi.fn();

    render(
      <RecommendationCard
        recommendation={{
          id: 1,
          campaign_id: 1,
          variant_id: 2,
          status: "PROPOSED",
          rank: 1,
          change_type: "CTA",
          target_component: "hero.cta_text",
          rationale: "Improve CTA",
          hypothesis: "Higher CTR",
          expected_impact_json: { ctr: "up" },
          patch_json: {
            operations: [{ op: "replace", path: "hero.cta_text", value: "Buy Now", reason: "clear action" }]
          }
        }}
        onApprove={onApprove}
        onReject={onReject}
        onApply={onApply}
        onFeedback={onFeedback}
        onPreview={onPreview}
      />
    );

    fireEvent.click(screen.getByText("Approve"));
    fireEvent.click(screen.getByText("Reject"));
    fireEvent.click(screen.getByText("Apply"));
    fireEvent.click(screen.getByText("Preview Change"));
    fireEvent.click(screen.getByRole("button", { name: "Helpful 👍" }));
    fireEvent.click(screen.getByRole("button", { name: "Not Helpful 👎" }));

    expect(onApprove).toHaveBeenCalledWith(1);
    expect(onReject).toHaveBeenCalledWith(1);
    expect(onApply).toHaveBeenCalledWith(1);
    expect(onPreview).toHaveBeenCalledWith(1);
    expect(onFeedback).toHaveBeenCalledWith(1, "POSITIVE");
    expect(onFeedback).toHaveBeenCalledWith(1, "NEGATIVE");
  });
});
