import { apiJson } from "./apiFetch";
import type { CheckInCreate, CheckInPublic, CheckInUpdate } from "./types";

export function submitCheckin(data: CheckInCreate): Promise<CheckInPublic> {
  return apiJson<CheckInPublic>("/checkins", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

/**
 * Redesign da Home (2026-09): a Home precisa ajustar um indicador
 * pontual (ex.: "como você está funcionando") sem reabrir o
 * formulário completo do check-in. Espelha `PATCH /checkins/{date}`,
 * que já existia no backend desde a ETAPA 11 — nenhuma rota nova.
 */
export function updateCheckin(checkinDate: string, data: CheckInUpdate): Promise<CheckInPublic> {
  return apiJson<CheckInPublic>(`/checkins/${checkinDate}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

/**
 * Espelha `GET /checkins` (já existia) — usado pela Home pra mostrar
 * um resumo curto da semana (quantos dias tiveram check-in) sem
 * recalcular nada, só listar o que já foi registrado.
 */
export function listCheckins(params: { dateFrom?: string; dateTo?: string; limit?: number } = {}): Promise<CheckInPublic[]> {
  const query = new URLSearchParams();
  if (params.dateFrom) query.set("date_from", params.dateFrom);
  if (params.dateTo) query.set("date_to", params.dateTo);
  if (params.limit) query.set("limit", String(params.limit));
  const qs = query.toString();
  return apiJson<CheckInPublic[]>(`/checkins${qs ? `?${qs}` : ""}`);
}
