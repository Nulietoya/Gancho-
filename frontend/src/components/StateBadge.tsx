import type { AlertState } from "../api/types";

const LABELS: Record<AlertState, string> = {
  green: "Dentro do seu padrão habitual",
  yellow: "Uma mudança sustentada no seu padrão",
  red: "Mudança em várias áreas ao mesmo tempo",
};

export function StateBadge({ state, reason }: { state: AlertState; reason: string }) {
  return (
    <div className={`state-badge state-badge--${state}`} role="status">
      <span className="state-badge__dot" aria-hidden="true" />
      <div>
        <p className="state-badge__label">{LABELS[state]}</p>
        <p className="state-badge__reason">{reason}</p>
      </div>
    </div>
  );
}
