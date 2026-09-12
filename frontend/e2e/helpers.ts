import { execFileSync } from "node:child_process";
import type { Page } from "@playwright/test";

/** Senha fixa que passa a validação de `RegisterPage` (8+ chars, letra e número). */
export const TEST_PASSWORD = "SenhaForte123!";

export function uniqueEmail(prefix: string): string {
  return `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}@example.com`;
}

/** Registra uma conta nova e espera cair no painel diário (`/`). */
export async function registerAccount(page: Page, email: string, password = TEST_PASSWORD): Promise<void> {
  await page.goto("/criar-conta");
  await page.fill('input[type="email"]', email);
  const passwordInputs = page.locator('input[type="password"]');
  const count = await passwordInputs.count();
  for (let i = 0; i < count; i++) {
    await passwordInputs.nth(i).fill(password);
  }
  await page.click('button[type="submit"]');
  await page.waitForURL(/\/$/, { timeout: 10_000 });
}

/**
 * O convite de pessoa de confiança (ETAPA 27, 2ª leva) nunca expõe o
 * `invite_token` de volta pra UI, e o cadastro v1 não manda e-mail
 * nenhum (decisão registrada desde a ETAPA 22) — em produção esse
 * token chegaria por um canal fora do produto. Pro teste, a única
 * forma de obtê-lo é lendo direto do Postgres local de desenvolvimento
 * (mesmas credenciais fixas de `backend/.env.example`), do mesmo jeito
 * que os scripts ad hoc desta sessão precisaram fazer manualmente.
 */
export function fetchInviteTokenFromDb(inviteEmail: string): string {
  const sql = `SELECT invite_token FROM trusted_person_relationships WHERE invite_email='${inviteEmail}' ORDER BY invited_at DESC LIMIT 1;`;
  const output = execFileSync("psql", ["-h", "localhost", "-U", "gancho", "-d", "gancho", "-tAc", sql], {
    env: { ...process.env, PGPASSWORD: "gancho" },
    encoding: "utf-8",
  });
  const token = output.trim();
  if (!token) {
    throw new Error(`nenhum invite_token encontrado pra ${inviteEmail} — o convite foi enviado?`);
  }
  return token;
}
