import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { describeError } from "../api/client";
import { getDailyDashboard } from "../api/dashboard";
import { notificationText } from "../api/notifications";
import type { DailyDashboard, MedicationEventStatus } from "../api/types";
import { MedicationDoseRow } from "../components/MedicationDoseRow";
import { StateBadge } from "../components/StateBadge";

export function DashboardPage() {
  const [data, setData] = useState<DailyDashboard | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getDailyDashboard()
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(describeError(err, "não foi possível carregar seu painel"));
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return <p className="page-loading">carregando…</p>;
  }
  if (error) {
    return (
      <p className="form-error" role="alert">
        {error}
      </p>
    );
  }
  if (!data) {
    return null;
  }

  function handleDoseConfirmed(scheduleId: string, status: MedicationEventStatus) {
    setData((prev) =>
      prev
        ? {
            ...prev,
            medications_today: prev.medications_today.map((dose) =>
              dose.schedule_id === scheduleId ? { ...dose, status } : dose,
            ),
          }
        : prev,
    );
  }

  return (
    <div className="dashboard-page">
      <StateBadge state={data.state} reason={data.state_reason} />

      <section className="card">
        <h2>Check-in de hoje</h2>
        {data.checkin_submitted_today ? (
          <p>Você já registrou seu check-in de hoje. Obrigado por continuar registrando.</p>
        ) : (
          <>
            <p>Você ainda não registrou como está hoje.</p>
            <Link className="button" to="/checkin">
              Fazer check-in
            </Link>
          </>
        )}
      </section>

      {data.medications_today.length > 0 && (
        <section className="card">
          <h2>Medicação de hoje</h2>
          <ul className="plain-list">
            {data.medications_today.map((dose) => (
              <MedicationDoseRow key={dose.schedule_id} dose={dose} onConfirmed={handleDoseConfirmed} />
            ))}
          </ul>
        </section>
      )}

      {data.active_interventions.length > 0 && (
        <section className="card">
          <h2>Em andamento</h2>
          <ul className="plain-list">
            {data.active_interventions.map((item) => (
              <li key={item.id}>{item.suggestion_text}</li>
            ))}
          </ul>
        </section>
      )}

      {data.unread_notifications_count > 0 && (
        <section className="card">
          <h2>Notificações</h2>
          <p>Você tem {data.unread_notifications_count} não lida{data.unread_notifications_count === 1 ? "" : "s"}.</p>
          <ul className="plain-list">
            {data.recent_notifications.filter((item) => !item.read_at).slice(0, 3).map((item) => (
              <li key={item.id}>{notificationText(item)}</li>
            ))}
          </ul>
          <Link className="button button--ghost" to="/notificacoes">Ver notificações</Link>
        </section>
      )}

    </div>
  );
}

