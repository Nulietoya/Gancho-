import { expect, test } from "@playwright/test";
import { fetchInviteTokenFromDb, registerAccount, uniqueEmail } from "./helpers";

/**
 * Formaliza os scripts ad hoc das levas 2ª e 6ª da ETAPA 27: convite
 * → aceitar → conceder permissão → a seção correspondente aparece
 * pro lado que RECEBE confiança só depois disso, nunca antes — é a
 * garantia central do produto ("nunca vê tudo por estar autenticada",
 * registrada em `docs/decisions.md` desde a ETAPA 23/24).
 */
test.describe("rede de confiança — convite e permissões granulares", () => {
  test("pessoa de confiança só ganha a ação depois que a permissão específica é concedida", async ({ browser }) => {
    const ownerEmail = uniqueEmail("e2e_owner");
    const trustedEmail = uniqueEmail("e2e_trusted");

    const ownerContext = await browser.newContext();
    const ownerPage = await ownerContext.newPage();
    await registerAccount(ownerPage, ownerEmail);

    await ownerPage.getByRole("link", { name: "Rede de confiança" }).click();
    await ownerPage.getByLabel("E-mail da pessoa").fill(trustedEmail);
    await ownerPage.getByRole("button", { name: "Enviar convite" }).click();
    await expect(ownerPage.getByText(trustedEmail)).toBeVisible();

    const inviteToken = fetchInviteTokenFromDb(trustedEmail);

    const trustedContext = await browser.newContext();
    const trustedPage = await trustedContext.newPage();
    await registerAccount(trustedPage, trustedEmail);
    await trustedPage.goto("/aceitar-convite");
    await trustedPage.getByLabel("Código do convite").fill(inviteToken);
    await trustedPage.getByRole("button", { name: "Aceitar convite" }).click();
    await expect(trustedPage.getByText("Convite aceito")).toBeVisible();

    await trustedPage.getByRole("link", { name: "Ver painel" }).click();
    await trustedPage.getByRole("link", { name: "Ver painel" }).click(); // WatchingListPage -> painel do relacionamento
    await expect(trustedPage).toHaveURL(/\/observando\/.+/);

    // sem permissão concedida ainda: nenhum formulário de observação
    await expect(trustedPage.getByRole("heading", { name: "Registrar uma observação" })).not.toBeVisible();

    // a lista de relacionamentos do dono é buscada uma vez, no mount —
    // recarrega pra pegar o status "accepted" que só existe desde que
    // a pessoa de confiança aceitou o convite, depois desse fetch.
    await ownerPage.reload();
    await expect(ownerPage.getByText(trustedEmail)).toBeVisible();

    // dono concede só "Registrar observações sobre você"
    await ownerPage.getByRole("button", { name: "Gerenciar permissões" }).click();
    await ownerPage.getByLabel("Registrar observações sobre você").check();
    await ownerPage.getByRole("button", { name: "Salvar permissões" }).click();
    await expect(ownerPage.getByText("salvo")).toBeVisible();

    // pessoa de confiança recarrega e agora vê exatamente essa seção — e só essa
    await trustedPage.reload();
    await expect(trustedPage.getByRole("heading", { name: "Registrar uma observação" })).toBeVisible();
    await expect(trustedPage.getByRole("heading", { name: "Sugerir uma tarefa" })).not.toBeVisible();

    await ownerContext.close();
    await trustedContext.close();
  });
});
