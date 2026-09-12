import { useEffect, useState, type FormEvent } from "react";
import {
  addPersonalPlanRule,
  createPersonalPlan,
  deactivatePersonalPlan,
  getPersonalPlan,
  updatePersonalPlan,
  updatePersonalPlanRule,
} from "../api/personalPlan";
import { describeError } from "../api/client";
import type { PersonalPlanPublic, PersonalPlanRulePublic, PersonalPlanSignal } from "../api/types";
import { PERSONAL_PLAN_SIGNAL_LABELS, PERSONAL_PLAN_SIGNAL_ORDER } from "../labels";

function PlanForm({
  initialTitle,
  initialDescription,
  submitLabel,
  onSubmit,
  onCancel,
}: {
  initialTitle: string;
  initialDescription: string;
  submitLabel: string;
  onSubmit: (title: string, description: string) => Promise<void>;
  onCancel?: () => void;
}) {
  const [title, setTitle] = useState(initialTitle);
  const [description, setDescription] = useState(initialDescription);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await onSubmit(title.trim(), description.trim());
    } catch (err) {
      setError(describeError(err, "não foi possível salvar o plano"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="invite-form" onSubmit={handleSubmit}>
      <label>
        Título
        <input type="text" value={title} onChange={(e) => setTitle(e.target.value)} required maxLength={150} />
      </label>
      <label>
        O que fazer / o que lembrar
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={6}
          required
          placeholder="Escreva pra você mesmo(a), como se estivesse explicando pra alguém que só vai ler isso quando você não conseguir perceber sozinho(a) que algo mudou."
        />
      </label>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      <div className="relationship-card__actions">
        <button type="submit" className="button" disabled={submitting}>
          {submitting ? "Salvando…" : submitLabel}
        </button>
        {onCancel && (
          <button type="button" className="button button--ghost" onClick={onCancel}>
            Cancelar
          </button>
        )}
      </div>
    </form>
  );
}

function AddRuleForm({ onAdded }: { onAdded: (rule: PersonalPlanRulePublic) => void }) {
  const [signalKey, setSignalKey] = useState<PersonalPlanSignal>(PERSONAL_PLAN_SIGNAL_ORDER[0]);
  const [thresholdDescription, setThresholdDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const rule = await addPersonalPlanRule({
        signal_key: signalKey,
        threshold_description: thresholdDescription.trim(),
      });
      onAdded(rule);
      setThresholdDescription("");
    } catch (err) {
      setError(describeError(err, "não foi possível adicionar o sinal"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="invite-form" onSubmit={handleSubmit}>
      <label>
        Área
        <select value={signalKey} onChange={(e) => setSignalKey(e.target.value as PersonalPlanSignal)}>
          {PERSONAL_PLAN_SIGNAL_ORDER.map((key) => (
            <option key={key} value={key}>
              {PERSONAL_PLAN_SIGNAL_LABELS[key]}
            </option>
          ))}
        </select>
      </label>
      <label>
        Quando considerar isso um sinal (nas suas palavras)
        <input
          type="text"
          value={thresholdDescription}
          onChange={(e) => setThresholdDescription(e.target.value)}
          placeholder='ex.: "faltei 2 dias seguidos ao trabalho"'
          required
          maxLength={500}
        />
      </label>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      <button type="submit" className="button button--ghost" disabled={submitting}>
        {submitting ? "Adicionando…" : "Adicionar sinal"}
      </button>
    </form>
  );
}

function RuleItem({ rule, onUpdated }: { rule: PersonalPlanRulePublic; onUpdated: (rule: PersonalPlanRulePublic) => void }) {
  const [toggling, setToggling] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleToggle() {
    setToggling(true);
    setError(null);
    try {
      const updated = await updatePersonalPlanRule(rule.id, { is_active: !rule.is_active });
      onUpdated(updated);
    } catch (err) {
      setError(describeError(err, "não foi possível atualizar o sinal"));
    } finally {
      setToggling(false);
    }
  }

  return (
    <li className={rule.is_active ? undefined : "rule-item--inactive"}>
      <strong>{PERSONAL_PLAN_SIGNAL_LABELS[rule.signal_key]}</strong>
      {!rule.is_active && <span className="status-badge status-badge--revoked">inativo</span>}
      <p>{rule.threshold_description}</p>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      <button type="button" className="button button--ghost" onClick={() => void handleToggle()} disabled={toggling}>
        {toggling ? "…" : rule.is_active ? "Desativar sinal" : "Reativar sinal"}
      </button>
    </li>
  );
}

export function PersonalPlanPage() {
  const [plan, setPlan] = useState<PersonalPlanPublic | null | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [confirmingDeactivate, setConfirmingDeactivate] = useState(false);
  const [deactivating, setDeactivating] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getPersonalPlan()
      .then((result) => {
        if (!cancelled) setPlan(result);
      })
      .catch((err) => {
        if (!cancelled) setError(describeError(err, "não foi possível carregar seu plano"));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  function handleRuleUpdated(updated: PersonalPlanRulePublic) {
    setPlan((prev) => (prev ? { ...prev, rules: prev.rules.map((r) => (r.id === updated.id ? updated : r)) } : prev));
  }

  async function handleDeactivate() {
    setDeactivating(true);
    setError(null);
    try {
      await deactivatePersonalPlan();
      setPlan(null);
    } catch (err) {
      setError(describeError(err, "não foi possível desativar o plano"));
    } finally {
      setDeactivating(false);
      setConfirmingDeactivate(false);
    }
  }

  return (
    <div className="trusted-people-page">
      <h1>Plano para quando eu não perceber</h1>
      <p className="checkin-hint">
        Escrito por você agora, enquanto está estável, pra guiar você (ou quem você autorizar a ver) numa hora em
        que talvez você não consiga perceber sozinho(a) que algo mudou.
      </p>

      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}

      {plan === undefined && !error && <p className="checkin-hint">carregando…</p>}

      {plan === null && (
        <section className="card">
          <h2>Você ainda não tem um plano ativo</h2>
          <PlanForm
            initialTitle=""
            initialDescription=""
            submitLabel="Salvar plano"
            onSubmit={async (title, description) => {
              const created = await createPersonalPlan({ title, description });
              setPlan(created);
            }}
          />
        </section>
      )}

      {plan && !editing && (
        <section className="card">
          <div className="relationship-card__header">
            <h2>{plan.title}</h2>
          </div>
          <p style={{ whiteSpace: "pre-wrap" }}>{plan.description}</p>
          <div className="relationship-card__actions">
            <button type="button" className="button button--ghost" onClick={() => setEditing(true)}>
              Editar
            </button>
          </div>
        </section>
      )}

      {plan && editing && (
        <section className="card">
          <h2>Editar plano</h2>
          <PlanForm
            initialTitle={plan.title}
            initialDescription={plan.description}
            submitLabel="Salvar alterações"
            onCancel={() => setEditing(false)}
            onSubmit={async (title, description) => {
              const updated = await updatePersonalPlan({ title, description });
              setPlan(updated);
              setEditing(false);
            }}
          />
        </section>
      )}

      {plan && (
        <section className="card">
          <h2>Sinais que você definiu</h2>
          <p className="checkin-hint">
            Nunca um número que o sistema calcula sozinho — sempre nas suas próprias palavras.
          </p>
          {plan.rules.length === 0 && <p className="checkin-hint">nenhum sinal cadastrado ainda.</p>}
          {plan.rules.length > 0 && (
            <ul className="plain-list">
              {plan.rules.map((rule) => (
                <RuleItem key={rule.id} rule={rule} onUpdated={handleRuleUpdated} />
              ))}
            </ul>
          )}
          <AddRuleForm onAdded={(rule) => setPlan((prev) => (prev ? { ...prev, rules: [...prev.rules, rule] } : prev))} />
        </section>
      )}

      {plan && (
        <section className="card">
          <h2>Desativar plano</h2>
          <p className="checkin-hint">
            Não há reativação — desativar um plano antigo sem revisá-lo contraria o espírito de "escrito enquanto
            estável". Desativando, você pode escrever um novo do zero quando quiser.
          </p>
          {confirmingDeactivate ? (
            <div className="relationship-card__revoke">
              <span>Tem certeza que quer desativar este plano?</span>
              <button
                type="button"
                className="button button--danger"
                onClick={() => void handleDeactivate()}
                disabled={deactivating}
              >
                {deactivating ? "Desativando…" : "Sim, desativar"}
              </button>
              <button type="button" className="button button--ghost" onClick={() => setConfirmingDeactivate(false)}>
                Cancelar
              </button>
            </div>
          ) : (
            <button type="button" className="button button--ghost" onClick={() => setConfirmingDeactivate(true)}>
              Desativar plano
            </button>
          )}
        </section>
      )}
    </div>
  );
}
