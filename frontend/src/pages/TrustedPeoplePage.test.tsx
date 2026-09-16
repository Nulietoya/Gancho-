import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { listTrustedPeople, revokeRelationship } from "../api/trustedPeople";
import type { OwnerRelationshipPublic, RelationshipPublic } from "../api/types";
import { TrustedPeoplePage } from "./TrustedPeoplePage";

vi.mock("../api/trustedPeople", async (importOriginal) => {
  const original = await importOriginal<typeof import("../api/trustedPeople")>();
  return {
    ...original,
    listTrustedPeople: vi.fn(),
    revokeRelationship: vi.fn(),
  };
});

const pendingRelationship: OwnerRelationshipPublic = {
  id: "r1",
  invite_email: "confianca@example.com",
  relationship_label: null,
  status: "pending",
  invited_at: "2026-01-01T00:00:00Z",
  accepted_at: null,
  revoked_at: null,
  permissions: [],
  invite_token: "token-de-teste-123",
};

beforeEach(() => {
  Object.assign(navigator, { clipboard: { writeText: vi.fn().mockResolvedValue(undefined) } });
});

it("mostra o link de convite (com botão de copiar) enquanto o convite está pendente", async () => {
  vi.mocked(listTrustedPeople).mockResolvedValue([pendingRelationship]);

  render(<TrustedPeoplePage />);

  expect(await screen.findByText(/aceitar-convite\?token=token-de-teste-123/)).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "Copiar link" }));
  await waitFor(() => expect(screen.getByRole("button", { name: "Copiado!" })).toBeInTheDocument());
  expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
    expect.stringContaining("/aceitar-convite?token=token-de-teste-123"),
  );
});

it("não mostra link nenhum para convites já aceitos (backend não reenvia token)", async () => {
  vi.mocked(listTrustedPeople).mockResolvedValue([
    { ...pendingRelationship, status: "accepted", accepted_at: "2026-01-02T00:00:00Z", invite_token: null },
  ]);

  render(<TrustedPeoplePage />);

  await screen.findByText("confianca@example.com");
  expect(screen.queryByText(/aceitar-convite\?token=/)).not.toBeInTheDocument();
});

it("some com o link na hora se o convite pendente for revogado, mesmo sem recarregar a lista", async () => {
  vi.mocked(listTrustedPeople).mockResolvedValue([pendingRelationship]);
  const revoked: RelationshipPublic = {
    id: "r1",
    invite_email: "confianca@example.com",
    relationship_label: null,
    status: "revoked",
    invited_at: "2026-01-01T00:00:00Z",
    accepted_at: null,
    revoked_at: "2026-01-03T00:00:00Z",
    permissions: [],
  };
  vi.mocked(revokeRelationship).mockResolvedValue(revoked);

  render(<TrustedPeoplePage />);
  await screen.findByText(/aceitar-convite\?token=/);

  fireEvent.click(screen.getByRole("button", { name: "Revogar acesso" }));
  fireEvent.click(screen.getByRole("button", { name: "Sim, revogar" }));

  await waitFor(() => expect(screen.queryByText(/aceitar-convite\?token=/)).not.toBeInTheDocument());
});
