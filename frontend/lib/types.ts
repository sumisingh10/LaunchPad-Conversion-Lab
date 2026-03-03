/**
 * Module overview for frontend/lib/types.ts.
 * Contains runtime logic for this feature area in LaunchPad Conversion Lab.
 */
export type Campaign = {
  id: number;
  name: string;
  product_title: string;
  product_category: string;
  product_description: string;
  objective: string;
  audience_segment: string;
  constraints_json: Record<string, unknown>;
  primary_kpi: string;
  status: string;
};

export type Variant = {
  id: number;
  campaign_id: number;
  name: string;
  strategy_tag: string;
  assets_json: any;
  source: string;
  created_at: string;
  updated_at: string;
};

export type MetricSnapshot = {
  id: number;
  campaign_id: number;
  variant_id: number;
  timestamp: string;
  impressions: number;
  clicks: number;
  add_to_cart: number;
  bounces: number;
  ctr: number;
  atc_rate: number;
  bounce_rate: number;
  source: string;
};

export type Recommendation = {
  id: number;
  campaign_id: number;
  variant_id: number;
  status: string;
  rank: number;
  change_type: string;
  target_component: string;
  rationale: string;
  hypothesis: string;
  expected_impact_json: Record<string, string>;
  patch_json: { operations: Array<{ op: string; path: string; value: string; reason: string }> };
};

export type FeedbackSummaryItem = {
  recommendation_id: number;
  positive_count: number;
  negative_count: number;
  avg_rating: number | null;
};

export type FeedbackItem = {
  id: number;
  recommendation_id: number;
  campaign_id: number;
  variant_id: number;
  user_id: number | null;
  sentiment: "POSITIVE" | "NEGATIVE";
  rating: number | null;
  comment: string | null;
  created_at: string;
};

export type LiftTraceEvent = {
  id: number;
  event_type: string;
  summary: string;
  created_at: string;
  actor_type: string;
  metadata_json?: Record<string, unknown>;
};

export type VariantVersionPerformance = {
  version_id: number;
  version_number: number;
  created_at: string;
  avg_ctr: number | null;
  avg_atc_rate: number | null;
  avg_bounce_rate: number | null;
  estimated_spend: number;
  sentiment_score: number | null;
};

export type OrgInsight = {
  change_type: string;
  segment: string;
  avg_ctr_lift: number;
  avg_atc_lift: number;
  avg_bounce_delta: number;
  avg_sentiment_delta: number;
};

export type CodexAuthStatus = {
  provider: "cli" | "api" | string;
  connected: boolean;
  fallback_enabled: boolean;
  cli_available?: boolean | null;
  has_cli_session?: boolean | null;
  has_api_key?: boolean | null;
};
