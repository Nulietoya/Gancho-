import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { listNotifications, markNotificationRead } from "../api/notifications";
import type { NotificationPublic } from "../api/types";
import { NotificationsPage } from "./NotificationsPage";

vi.mock("../api/notifications", async (importOriginal) => {
  const original = await importOriginal<typeof import("../api/notifications")>();
  return { ...original, listNotifications: vi.fn(), markNotificationRead: vi.fn() };
});

const notification: NotificationPublic = {
  id: "n1",
  type: "alert",
  channel: "in_app",
  priority: "medium",
  payload: { reason_summary: "Seu estado mudou." },
  grouped_with: null,
  scheduled_for: null,
  sent_at: null,
  read_at: null,
  created_at: "2026-01-01T00:00:00Z",
};

beforeEach(() => {
  vi.mocked(listNotifications).mockResolvedValue([notification]);
  vi.mocked(markNotificationRead).mockResolvedValue({ ...notification, read_at: "2026-01-01T01:00:00Z" });
});

it("mostra o conteúdo e permite marcar a notificação como lida", async () => {
  render(<NotificationsPage />);
  expect(await screen.findByText("Seu estado mudou.")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Marcar como lida" }));
  await waitFor(() => expect(screen.queryByRole("button", { name: "Marcar como lida" })).not.toBeInTheDocument());
  expect(markNotificationRead).toHaveBeenCalledWith("n1");
});

