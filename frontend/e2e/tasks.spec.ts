import { expect, test } from "@playwright/test";
import { registerAccount, uniqueEmail } from "./helpers";

/**
 * Formaliza o script ad hoc da ETAPA 27 (8ª leva): cria uma tarefa e
 * percorre a máquina de estados real do backend (`task_service.py`)
 * clicando só nos botões que a UI decide mostrar — não reimplementa a
 * transição aqui, só confere que ela acontece.
 */
test.describe("tarefas — ciclo de vida", () => {
  test("criar → iniciar → pausar → retomar → adiar com motivo → concluir", async ({ page }) => {
    await registerAccount(page, uniqueEmail("e2e_tasks"));
    await page.getByRole("link", { name: "Missões" }).click();
    await expect(page).toHaveURL(/\/tarefas$/);

    await page.getByLabel("Título").fill("Lavar louça");
    await page.getByRole("button", { name: "Criar tarefa" }).click();

    const card = page.locator(".relationship-card", { hasText: "Lavar louça" });
    const badge = card.locator(".status-badge");
    await expect(card).toBeVisible();
    await expect(badge).toHaveText("Pendente");

    await card.getByRole("button", { name: "Iniciar" }).click();
    await expect(badge).toHaveText("Em andamento");

    await card.getByRole("button", { name: "Pausar" }).click();
    await expect(badge).toHaveText("Pausada");

    await card.getByRole("button", { name: "Retomar" }).click();
    await expect(badge).toHaveText("Em andamento");

    await card.getByRole("button", { name: "Adiar" }).click();
    await card.getByRole("button", { name: "Confirmar adiamento" }).click();
    await expect(badge).toHaveText("Adiada");
    await expect(card.getByText("adiada 1x")).toBeVisible();

    await card.getByRole("button", { name: "Concluir" }).click();
    await expect(badge).toHaveText("Concluída");

    // tarefa concluída é terminal: nenhum botão de ação sobra
    await expect(card.getByRole("button")).toHaveCount(0);
  });

  test("cancelar exige confirmação de dois passos", async ({ page }) => {
    await registerAccount(page, uniqueEmail("e2e_tasks_cancel"));
    await page.getByRole("link", { name: "Missões" }).click();

    await page.getByLabel("Título").fill("Tarefa a cancelar");
    await page.getByRole("button", { name: "Criar tarefa" }).click();

    const card = page.locator(".relationship-card", { hasText: "Tarefa a cancelar" });
    const badge = card.locator(".status-badge");
    await card.getByRole("button", { name: "Cancelar tarefa" }).click();

    // primeiro clique só abre a confirmação — ainda não cancelou
    await expect(badge).toHaveText("Pendente");
    await expect(card.getByText("Cancelar esta tarefa?")).toBeVisible();

    await card.getByRole("button", { name: "Sim, cancelar" }).click();
    await expect(badge).toHaveText("Cancelada");
  });
});
