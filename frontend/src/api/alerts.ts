import { apiJson } from "./apiFetch";
import { ApiError } from "./client";
import type { AlertExplanation, AlertPublic } from "./types";

export async function getCurrentAlert(): Promise<AlertPublic | null> {
  try {
    return await apiJson<AlertPublic>("/alerts/current");
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) {
      return null;
    }
    throw err;
  }
}

export function listAlertHistory(limit = 30): Promise<AlertPublic[]> {
  return apiJson<AlertPublic[]>(`/alerts?limit=${limit}`);
}

export function syncAlertState(): Promise<AlertPublic> {
  return apiJson<AlertPublic>("/alerts/sync", { method: "POST" });
}

export function acknowledgeAlert(alertId: string): Promise<AlertPublic> {
  return apiJson<AlertPublic>(`/alerts/${alertId}/acknowledge`, { method: "POST" });
}

export function resolveAlert(alertId: string): Promise<AlertPublic> {
  return apiJson<AlertPublic>(`/alerts/${alertId}/resolve`, { method: "POST" });
}

export function explainAlert(alertId: string): Promise<AlertExplanation> {
  return apiJson<AlertExplanation>(`/alerts/${alertId}/explanation`);
}
