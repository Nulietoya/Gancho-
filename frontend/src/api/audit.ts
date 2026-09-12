import { apiJson } from "./apiFetch";
import type { AuditLogEntry } from "./types";

/** `GET /audit-log` — sempre só da PRÓPRIA conta, nunca do que o usuário fez como pessoa de confiança de outra. */
export function listAuditLog(limit: number, offset: number): Promise<AuditLogEntry[]> {
  return apiJson<AuditLogEntry[]>(`/audit-log?limit=${limit}&offset=${offset}`);
}
