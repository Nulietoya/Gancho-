import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import * as client from "../api/client";
import { useAuthStore } from "../store/authStore";
import { LoginPage } from "./LoginPage";

afterEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
  useAuthStore.setState({ accessToken: null, refreshToken: null, user: null, status: "idle", error: null });
});

/**
 * Regressão do bug real: antes, `LoginPage` sempre mandava pra "/"
 * depois de entrar, então quem chegava aqui vindo de
 * `/aceitar-convite?token=...` (redirecionado pelo `ProtectedRoute`,
 * que jogava fora o token) nunca mais voltava pro convite sozinho.
 */
it("depois de entrar, volta pro ?redirect= (não sempre pro painel)", async () => {
  vi.spyOn(client, "rawJson")
    .mockResolvedValueOnce({ access_token: "a", refresh_token: "b", token_type: "bearer" })
    .mockResolvedValueOnce({ id: "u1", email: "confianca@example.com", created_at: "2026-01-01T00:00:00Z" });

  render(
    <MemoryRouter initialEntries={["/entrar?redirect=%2Faceitar-convite%3Ftoken%3Dxyz"]}>
      <Routes>
        <Route path="/entrar" element={<LoginPage />} />
        <Route path="/aceitar-convite" element={<p>tela de aceitar convite</p>} />
        <Route path="/" element={<p>painel</p>} />
      </Routes>
    </MemoryRouter>,
  );

  fireEvent.change(screen.getByLabelText("E-mail"), { target: { value: "confianca@example.com" } });
  fireEvent.change(screen.getByLabelText("Senha"), { target: { value: "senhaForte123" } });
  fireEvent.click(screen.getByRole("button", { name: "Entrar" }));

  await waitFor(() => expect(screen.getByText("tela de aceitar convite")).toBeInTheDocument());
  expect(screen.queryByText("painel")).not.toBeInTheDocument();
});

it("nunca segue um redirect pra fora do próprio app (trava contra //evil.com)", async () => {
  vi.spyOn(client, "rawJson")
    .mockResolvedValueOnce({ access_token: "a", refresh_token: "b", token_type: "bearer" })
    .mockResolvedValueOnce({ id: "u1", email: "x@example.com", created_at: "2026-01-01T00:00:00Z" });

  render(
    <MemoryRouter initialEntries={["/entrar?redirect=%2F%2Fevil.com"]}>
      <Routes>
        <Route path="/entrar" element={<LoginPage />} />
        <Route path="/" element={<p>painel</p>} />
      </Routes>
    </MemoryRouter>,
  );

  fireEvent.change(screen.getByLabelText("E-mail"), { target: { value: "x@example.com" } });
  fireEvent.change(screen.getByLabelText("Senha"), { target: { value: "senhaForte123" } });
  fireEvent.click(screen.getByRole("button", { name: "Entrar" }));

  await waitFor(() => expect(screen.getByText("painel")).toBeInTheDocument());
});
