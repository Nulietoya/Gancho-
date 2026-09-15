import { apiJson } from "./apiFetch";
import type { NotificationPublic } from "./types";

export function listNotifications(): Promise<NotificationPublic[]> {
  return apiJson("/notifications");
}

export function markNotificationRead(id: string): Promise<NotificationPublic> {
  return apiJson(`/notifications/${id}/read`, { method: "POST" });
}

export function notificationText(notification: NotificationPublic): string {
  const reason = notification.payload.reason_summary;
  const message = notification.payload.message;
  if (typeof reason === "string" && reason.trim()) return reason;
  if (typeof message === "string" && message.trim()) return message;
  return notification.type === "alert" ? "Seu estado foi atualizado." : "Nova notificação.";
}

