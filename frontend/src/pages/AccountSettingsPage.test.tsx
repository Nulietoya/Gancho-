import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import * as accountApi from "../api/account";
import { useAuthStore } from "../store/authStore";
import { AccountSettingsPage } from "./AccountSettingsPage";

afterEach(() => {
  vi.restoreAllMocks();
  useAuthStore.setState({ accessToken: null, refreshToken: null, user: null, status: "idle", error: null });
});

function renderPage() {
  render(
    <MemoryRouter initialEntries={["/configuracoes"]}>
      <Routes>
        <Route path="/configuracoes" element={<AccountSettingsPage />} />
        <Route path="/entrar" element={<p>tela de entrar</p>} />
      </Routes>
    </MemoryRouter>,
  );
}

/**
 * Decisão revertida em 2026-09-22: exclusão virou apagamento físico
 * de verdade (era soft delete). A UI ganhou uma segunda barreira —
 * digitar "EXCLUIR" — proporcional ao fato de não existir mais
 * "desfazer depois". Regressão a evitar: reativar o botão de excluir
 * antes da palavra de confirmação bater iria contra o próprio motivo
 * dela existir.
 */
it("mantém o botão de excluir desabilitado até digitar a palavra de confirmação", () => {
  renderPage();
  fireEvent.click(screen.getByRole("button", { name: "Excluir minha conta" }));

  fireEvent.change(screen.getByLabelText("Confirme sua senha"), { target: { value: "senhaForte123" } });
  const submitButton = screen.getByRole("button", { name: "Sim, excluir minha conta para sempre" });
  expect(submitButton).toBeDisabled();

  fireEvent.change(screen.getByLabelText(/Digite/), { target: { value: "excluir" } });
  expect(submitButton).toBeDisabled(); // case-sensitive de propósito — sem "quase certo"

  fireEvent.change(screen.getByLabelText(/Digite/), { target: { value: "EXCLUIR" } });
  expect(submitButton).not.toBeDisabled();
});

it("chama a API de exclusão e leva pra tela de entrar quando confirmado", async () => {
  const deleteSpy = vi.spyOn(accountApi, "deleteAccount").mockResolvedValueOnce({ deleted: true });
  useAuthStore.setState({ logout: vi.fn().mockResolvedValue(undefined) });

  renderPage();
  fireEvent.click(screen.getByRole("button", { name: "Excluir minha conta" }));
  fireEvent.change(screen.getByLabelText("Confirme sua senha"), { target: { value: "senhaForte123" } });
  fireEvent.change(screen.getByLabelText(/Digite/), { target: { value: "EXCLUIR" } });
  fireEvent.click(screen.getByRole("button", { name: "Sim, excluir minha conta para sempre" }));

  await waitFor(() => expect(screen.getByText("tela de entrar")).toBeInTheDocument());
  expect(deleteSpy).toHaveBeenCalledWith({ password: "senhaForte123" });
});

it("mostra o erro do backend e não navega quando a senha está errada", async () => {
  vi.spyOn(accountApi, "deleteAccount").mockRejectedValueOnce(new Error("senha incorreta"));

  renderPage();
  fireEvent.click(screen.getByRole("button", { name: "Excluir minha conta" }));
  fireEvent.change(screen.getByLabelText("Confirme sua senha"), { target: { value: "senhaErrada" } });
  fireEvent.change(screen.getByLabelText(/Digite/), { target: { value: "EXCLUIR" } });
  fireEvent.click(screen.getByRole("button", { name: "Sim, excluir minha conta para sempre" }));

  await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
  expect(screen.queryByText("tela de entrar")).not.toBeInTheDocument();
});
