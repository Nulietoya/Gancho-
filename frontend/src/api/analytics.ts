import { apiJson } from "./apiFetch";
import type { AnalyticsDashboard } from "./types";

export function getAnalyticsDashboard(days: number): Promise<AnalyticsDashboard> {
  return apiJson<AnalyticsDashboard>(`/dashboard/analytics?days=${days}`);
}
