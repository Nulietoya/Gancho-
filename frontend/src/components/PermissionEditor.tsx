import { useEffect, useState } from "react";
import type { IndicatorKey, PermissionKey, PermissionPublic, PermissionUpdate } from "../api/types";
import { INDICATOR_LABELS, INDICATOR_ORDER, PERMISSION_LABELS, PERMISSION_ORDER } from "../labels";

type LocalPermission = { is_granted: boolean; indicator_scope: IndicatorKey[] | null };
type LocalState = Record<PermissionKey, LocalPermission>;

function buildLocalState(permissions: PermissionPublic[]): LocalState {
  const byKey = new Map(permissions.map((p) => [p.permission_key, p]));
  const state = {} as LocalState;
  for (const key of PERMISSION_ORDER) {
    const existing = byKey.get(key);
    state[key] = {
      is_granted: existing?.is_granted ?? false,
      indicator_scope: existing?.indicator_scope ?? null,
    };
  }
  return state;
}

export function PermissionEditor({
  permissions,
  onSave,
}: {
  permissions: PermissionPublic[];
  onSave: (updates: PermissionUpdate[]) => Promise<void>;
}) {
  const [local, setLocal] = useState<LocalState>(() => buildLocalState(permissions));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  // sincroniza quando o relacionamento é recarregado do backend (ex.: logo
  // após salvar) — nunca durante edição em andamento, porque `permissions`
  // só muda quando o pai recebe uma resposta nova da API.
  useEffect(() => {
    setLocal(buildLocalState(permissions));
  }, [permissions]);

  function toggle(key: PermissionKey) {
    setSaved(false);
    setLocal((prev) => ({ ...prev, [key]: { ...prev[key], is_granted: !prev[key].is_granted } }));
  }

  function toggleIndicator(indicator: IndicatorKey) {
    setSaved(false);
    setLocal((prev) => {
      const current = prev.view_specific_indicators.indicator_scope ?? [];
      const next = current.includes(indicator) ? current.filter((i) => i !== indicator) : [...current, indicator];
      return {
        ...prev,
        view_specific_indicators: { ...prev.view_specific_indicators, indicator_scope: next },
      };
    });
  }

  async function handleSave() {
    setSaving(true);
    setError(null);
    setSaved(false);
    const updates: PermissionUpdate[] = PERMISSION_ORDER.map((key) => ({
      permission_key: key,
      is_granted: local[key].is_granted,
      indicator_scope: key === "view_specific_indicators" ? local[key].indicator_scope : null,
    }));
    try {
      await onSave(updates);
      setSaved(true);
    } catch {
      setError("não foi possível salvar as permissões, tente de novo");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="permission-editor">
      <ul className="permission-list">
        {PERMISSION_ORDER.map((key) => (
          <li key={key} className="permission-item">
            <label className="permission-checkbox">
              <input type="checkbox" checked={local[key].is_granted} onChange={() => toggle(key)} />
              {PERMISSION_LABELS[key]}
            </label>
            {key === "view_specific_indicators" && local[key].is_granted && (
              <div className="indicator-scope">
                {INDICATOR_ORDER.map((indicator) => (
                  <label key={indicator} className="indicator-checkbox">
                    <input
                      type="checkbox"
                      checked={(local.view_specific_indicators.indicator_scope ?? []).includes(indicator)}
                      onChange={() => toggleIndicator(indicator)}
                    />
                    {INDICATOR_LABELS[indicator]}
                  </label>
                ))}
              </div>
            )}
          </li>
        ))}
      </ul>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      <div className="permission-editor__actions">
        <button type="button" className="button" onClick={() => void handleSave()} disabled={saving}>
          {saving ? "Salvando…" : "Salvar permissões"}
        </button>
        {saved && <span className="permission-editor__saved">salvo</span>}
      </div>
    </div>
  );
}
