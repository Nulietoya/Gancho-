import { apiJson } from "./apiFetch";
import type { AccountDeactivateRequest, AccountDeactivateResponse, ChangePasswordRequest } from "./types";

export function changePassword(data: ChangePasswordRequest): Promise<void> {
  return apiJson<void>("/auth/change-password", { method: "POST", body: JSON.stringify(data) });
}

export function deactivateAccount(data: AccountDeactivateRequest): Promise<AccountDeactivateResponse> {
  return apiJson<AccountDeactivateResponse>("/account/deactivate", { method: "POST", body: JSON.stringify(data) });
}

/**
 * Item 53 — exportação. O backend devolve um JSON síncrono (sem
 * `Content-Disposition`, sem job assíncrono — volume de um MVP não
 * justifica isso), então o download é montado aqui: busca o retrato
 * via `apiJson` (token + retry-401 de graça) e dispara o download
 * como Blob local, sem duplicar essa lógica.
 */
export async function exportAndDownloadAccountData(): Promise<void> {
  const data = await apiJson<Record<string, unknown>>("/account/export");
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `gancho-meus-dados-${new Date().toISOString().slice(0, 10)}.json`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
