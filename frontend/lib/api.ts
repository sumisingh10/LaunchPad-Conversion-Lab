/**
 * Module overview for frontend/lib/api.ts.
 * Contains runtime logic for this feature area in LaunchPad Conversion Lab.
 */
import { clearToken, getToken } from "./auth";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken();
  const headers = new Headers(init?.headers || {});
  headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`${API_BASE}${path}`, { ...init, headers, cache: "no-store" });
  if (!res.ok) {
    if (res.status === 401 && path.startsWith("/auth/login")) {
      throw new Error("Invalid email or password. Please try again.");
    }
    if (res.status === 401) {
      clearToken();
      if (typeof window !== "undefined" && window.location.pathname !== "/") {
        window.location.href = "/";
      }
      throw new Error("Your session expired. Please sign in again.");
    }
    const body = await res.text();
    if (body) {
      let detail = "";
      try {
        const parsed = JSON.parse(body);
        detail = typeof parsed?.detail === "string" ? parsed.detail : "";
      } catch {
        // Keep plain-text fallback below if response is not JSON.
      }
      if (detail) throw new Error(detail);
      if (body.startsWith("{\"detail\":")) {
        const stripped = body.replace(/^{"detail":"?/, "").replace(/"}$/, "");
        throw new Error(stripped || body);
      }
      throw new Error(body);
    }
    throw new Error(`Request failed: ${res.status}`);
  }
  return res.json();
}

export const api = {
  signup: (payload: any) => request<{ access_token: string }>("/auth/signup", { method: "POST", body: JSON.stringify(payload) }),
  login: (payload: any) => request<{ access_token: string }>("/auth/login", { method: "POST", body: JSON.stringify(payload) }),
  me: () => request<any>("/auth/me"),
  listCampaigns: () => request<any[]>("/campaigns"),
  createCampaign: (payload: any) => request<any>("/campaigns", { method: "POST", body: JSON.stringify(payload) }),
  deleteCampaign: (id: number) => request<any>(`/campaigns/${id}`, { method: "DELETE" }),
  getCampaign: (id: number) => request<any>(`/campaigns/${id}`),
  setBaseline: (campaignId: number, variantId: number, baselineName?: string) =>
    request<any>(`/campaigns/${campaignId}/baseline`, {
      method: "POST",
      body: JSON.stringify({ variant_id: variantId, baseline_name: baselineName || undefined }),
    }),
  revertBaseline: (campaignId: number) => request<any>(`/campaigns/${campaignId}/baseline/revert`, { method: "POST" }),
  orgInsights: (campaignId: number) => request<any[]>(`/campaigns/${campaignId}/org-insights`),
  listVariants: (campaignId: number) => request<any[]>(`/campaigns/${campaignId}/variants`),
  deleteVariant: (variantId: number) => request<any>(`/variants/${variantId}`, { method: "DELETE" }),
  generateVariants: (campaignId: number) => request<any[]>(`/campaigns/${campaignId}/generate-variants`, { method: "POST" }),
  simulateBatch: (campaignId: number) => request<any[]>(`/campaigns/${campaignId}/simulate-batch`, { method: "POST" }),
  listMetrics: (campaignId: number) => request<any[]>(`/campaigns/${campaignId}/metrics`),
  analyze: (campaignId: number) => request<any[]>(`/campaigns/${campaignId}/analyze-kpis`, { method: "POST" }),
  propose: (
    campaignId: number,
    payload?: { user_goal?: string; landing_page_snapshot_url?: string; focus_component?: string; selected_variant_id?: number }
  ) =>
    request<any[]>(`/campaigns/${campaignId}/propose-improvements`, { method: "POST", body: JSON.stringify(payload || {}) }),
  adviseVariants: (campaignId: number, payload: { user_goal: string; variant_ids?: number[] }) =>
    request<any>(`/campaigns/${campaignId}/advise-variants`, { method: "POST", body: JSON.stringify(payload) }),
  startAdviseVariantsJob: (campaignId: number, payload: { user_goal: string; variant_ids?: number[] }) =>
    request<any>(`/campaigns/${campaignId}/advise-variants/jobs`, { method: "POST", body: JSON.stringify(payload) }),
  getAdviseVariantsJob: (campaignId: number, jobId: string) =>
    request<any>(`/campaigns/${campaignId}/advise-variants/jobs/${jobId}`),
  autoOptimize: (campaignId: number, payload: { user_goal: string; preferred_variant_id?: number }) =>
    request<any>(`/campaigns/${campaignId}/auto-optimize`, { method: "POST", body: JSON.stringify(payload) }),
  startAutoOptimizeJob: (campaignId: number, payload: { user_goal: string; preferred_variant_id?: number }) =>
    request<any>(`/campaigns/${campaignId}/auto-optimize/jobs`, { method: "POST", body: JSON.stringify(payload) }),
  getAutoOptimizeJob: (campaignId: number, jobId: string) =>
    request<any>(`/campaigns/${campaignId}/auto-optimize/jobs/${jobId}`),
  listRecommendations: (campaignId: number) => request<any[]>(`/campaigns/${campaignId}/recommendations`),
  approveRecommendation: (id: number) => request<any>(`/recommendations/${id}/approve`, { method: "POST" }),
  rejectRecommendation: (id: number) => request<any>(`/recommendations/${id}/reject`, { method: "POST" }),
  applyRecommendation: (id: number, payload?: { variant_name?: string }) =>
    request<any>(`/recommendations/${id}/apply`, { method: "POST", body: JSON.stringify(payload || {}) }),
  saveRecommendationVariant: (id: number, payload?: { variant_name?: string }) =>
    request<any>(`/recommendations/${id}/save-variant`, { method: "POST", body: JSON.stringify(payload || {}) }),
  feedbackRecommendation: (id: number, payload: any) =>
    request<any>(`/recommendations/${id}/feedback`, { method: "POST", body: JSON.stringify(payload) }),
  feedbackSummary: (campaignId: number) => request<any[]>(`/campaigns/${campaignId}/feedback-summary`),
  listFeedback: (campaignId: number) => request<any[]>(`/campaigns/${campaignId}/feedback`),
  manualEditVariant: (variantId: number, payload: { path: string; value: string; reason?: string }) =>
    request<any>(`/variants/${variantId}/manual-edit`, { method: "POST", body: JSON.stringify(payload) }),
  submitVariantForAdminApproval: (variantId: number) =>
    request<any>(`/variants/${variantId}/submit-admin-approval`, { method: "POST" }),
  getVariantAdminApprovalStatus: (variantId: number) =>
    request<any>(`/variants/${variantId}/admin-approval-status`),
  variantVersionPerformance: (variantId: number) => request<any[]>(`/variants/${variantId}/version-performance`),
  liftTrace: (campaignId: number) => request<any[]>(`/campaigns/${campaignId}/lift-trace`),
  codexAuthStatus: () => request<any>("/system/codex-auth-status")
};
