import { expect, test } from "@playwright/test";
import { registerAccount, uniqueEmail } from "./helpers";

/**
 * Fluxo mais básico do produto, formalizado a partir do script ad hoc
 * da 1ª leva da ETAPA 27 (que já tinha achado um bug real ali: o
 * StrictMode duplicando o refresh de token). Cobre cadastro, sessão
 * persistindo num reload, check-in, e logout.
 */
test.describe("autenticação e check-in", () => {
  test("cadastro leva ao painel diário, sessão sobrevive a um reload, e logout volta pro login", async ({ page }) => {
    const email = uniqueEmail("e2e_auth");
    await registerAccount(page, email);

    await expect(page.getByText(email)).toBeVisible();

    // sessão persiste num reload de página (token de refresh em localStorage)
    await page.reload();
    await expect(page).toHaveURL(/\/$/);
    await expect(page.getByText(email)).toBeVisible();

    await page.getByRole("button", { name: "Sair" }).click();
    await expect(page).toHaveURL(/\/entrar$/);
  });

  test("submeter check-in parcial (só um indicador) é aceito e volta pro painel", async ({ page }) => {
    const email = uniqueEmail("e2e_checkin");
    await registerAccount(page, email);

    await page.getByRole("link", { name: "Check-in" }).click();
    await expect(page).toHaveURL(/\/checkin$/);

    // preenche só "Humor" com nota 4 — o formulário aceita qualquer
    // subconjunto de indicadores, nenhum é obrigatório (documentado
    // no próprio texto da tela). "Humor" é um <legend> de <fieldset>,
    // não um heading — por isso o locator por texto no fieldset.
    await page.locator("fieldset", { hasText: "Humor" }).getByRole("button", { name: "4", exact: true }).click();
    await page.getByRole("button", { name: "Salvar check-in" }).click();

    await expect(page.getByText("Check-in salvo")).toBeVisible();
    await expect(page).toHaveURL(/\/$/, { timeout: 5_000 });
    await expect(page.getByText("Você já registrou seu check-in de hoje")).toBeVisible();
  });

  test("submeter check-in vazio mostra erro em vez de salvar", async ({ page }) => {
    const email = uniqueEmail("e2e_checkin_vazio");
    await registerAccount(page, email);

    await page.getByRole("link", { name: "Check-in" }).click();
    await page.getByRole("button", { name: "Salvar check-in" }).click();

    await expect(page.getByText("preencha pelo menos um indicador")).toBeVisible();
    await expect(page).toHaveURL(/\/checkin$/); // não navegou
  });
});
