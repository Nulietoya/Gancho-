import { apiJson } from "./apiFetch";
import type { DeviationEventPublic, EngineExplanation } from "./types";

export function runAllEngines(): Promise<DeviationEventPublic[]> {
  return apiJson<DeviationEventPublic[]>("/deviation/run", { method: "POST" });
}

export function explainDeviationEvent(eventId: string): Promise<EngineExplanation> {
  return apiJson<EngineExplanation>(`/deviation/events/${eventId}/explanation`);
}
