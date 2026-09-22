import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";
import { acceptInvite, previewInvite } from "../api/trustedPeople";
import type { InvitePreview, RelationshipAsTrustedPublic, UserPublic } from "../api/types";
import { useAuthStore } from "../store/authStore";
import { AcceptInvitePage } from "./AcceptInvitePage";

vi.mock("../api/trustedPeople", async (importOriginal) => {
  const original = await importOriginal<typeof import("../api/trustedPeople")>();
  return { ...original, previewInvite: vi.fn(), acceptInvite: vi.fn() };
});

const owner = "Nulie";
const invitedEmail = "confianca@example.com";
const preview: InvitePreview = { invite_email: invitedEmail, owner_display_name: owner, status: "pending" };

const baseAuthState = {
  accessToken: null,
  refreshToken: null,
  user: null as UserPublic | null,
  error: null,
};

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AcceptInvitePage />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.mocked(previewInvite).mockResolvedValue(preview);
});

it(
  "sem sessão: mostra de quem é o convite e leva pro login/cadastro preservando o link e o e-mail convidado",
  async () => {
    useAuthStore.setState({ ...baseAuthState, status: "unauthenticated" });

    renderAt("/aceitar-convite?token=abc123");

    await screen.findByText(/Convite de/);
    expect(screen.getByText(owner)).toBeInTheDocument();
    expect(screen.getByText(invitedEmail)).toBeInTheDocument();
    expect(previewInvite).toHaveBeenCalledWith("abc123");

    const loginLink = screen.getByRole("link", { name: "Entrar" });
    const href = loginLink.getAttribute("href")!;
    expect(href).toContain(`redirect=${encodeURIComponent("/aceitar-convite?token=abc123")}`);
    expect(href).toContain(`email=${encodeURIComponent(invitedEmail)}`);

    const registerLink = screen.getByRole("link", { name: "Criar conta" });
    expect(registerLink.getAttribute("href")).toContain(
      `redirect=${encodeURIComponent("/aceitar-convite?token=abc123")}`,
    );
  },
);

it("logado com e-mail diferente do convite: avisa o descompasso e não deixa tentar aceitar", async () => {
  useAuthStore.setState({
    ...baseAuthState,
    status: "authenticated",
    user: { id: "u1", email: "outro@example.com", created_at: "2026-01-01T00:00:00Z" },
    logout: vi.fn().mockResolvedValue(undefined),
  });

  renderAt("/aceitar-convite?token=abc123");

  await screen.findByText(/está logado como/);
  expect(screen.getByText("outro@example.com")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Aceitar convite" })).not.toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "Sair" }));
  expect(useAuthStore.getState().logout).toHaveBeenCalled();
});

it("logado com o e-mail certo: aceita o convite e mostra a identidade do DONO, não o próprio e-mail", async () => {
  useAuthStore.setState({
    ...baseAuthState,
    status: "authenticated",
    user: { id: "u1", email: invitedEmail, created_at: "2026-01-01T00:00:00Z" },
  });
  const accepted: RelationshipAsTrustedPublic = {
    id: "r1",
    invite_email: invitedEmail,
    relationship_label: null,
    status: "accepted",
    invited_at: "2026-01-01T00:00:00Z",
    accepted_at: "2026-01-02T00:00:00Z",
    revoked_at: null,
    permissions: [],
    owner_display_name: owner,
  };
  vi.mocked(acceptInvite).mockResolvedValue(accepted);

  renderAt("/aceitar-convite?token=abc123");

  const button = await screen.findByRole("button", { name: "Aceitar convite" });
  fireEvent.click(button);

  await waitFor(() => expect(screen.getByText(owner)).toBeInTheDocument());
  expect(screen.queryByText(invitedEmail)).not.toBeInTheDocument();
});
