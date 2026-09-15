import { useEffect, useState } from "react";
import { describeError } from "../api/client";
import { listNotifications, markNotificationRead, notificationText } from "../api/notifications";
import type { NotificationPublic } from "../api/types";

export function NotificationsPage() {
  const [notifications, setNotifications] = useState<NotificationPublic[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [actingId, setActingId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    listNotifications()
      .then((items) => {
        if (!cancelled) setNotifications(items);
      })
      .catch((err) => {
        if (!cancelled) setError(describeError(err, "não foi possível carregar as notificações"));
      });
    return () => { cancelled = true; };
  }, []);

  async function markRead(id: string) {
    setActingId(id);
    setError(null);
    try {
      const updated = await markNotificationRead(id);
      setNotifications((items) => items?.map((item) => item.id === id ? updated : item) ?? null);
    } catch (err) {
      setError(describeError(err, "não foi possível marcar como lida"));
    } finally {
      setActingId(null);
    }
  }

  return (
    <div>
      <h1>Notificações</h1>
      {error && <p className="form-error" role="alert">{error}</p>}
      {notifications === null && !error && <p className="page-loading">carregando…</p>}
      {notifications?.length === 0 && <p className="checkin-hint">Nenhuma notificação ainda.</p>}
      {notifications && notifications.length > 0 && (
        <ul className="relationship-list">
          {notifications.map((item) => (
            <li key={item.id} className={`card notification-card${item.read_at ? "" : " notification-card--unread"}`}>
              <p>{notificationText(item)}</p>
              <p className="relationship-card__dates">{new Date(item.created_at).toLocaleString("pt-BR")}</p>
              {!item.read_at && (
                <button type="button" className="button button--ghost" disabled={actingId === item.id}
                  onClick={() => void markRead(item.id)}>
                  {actingId === item.id ? "Marcando…" : "Marcar como lida"}
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

