import { apiJson } from "./apiFetch";
import type { DailyDashboard } from "./types";

export function getDailyDashboard(): Promise<DailyDashboard> {
  return apiJson<DailyDashboard>("/dashboard/daily");
}
