import { useEffect, useMemo, useRef, useState } from "react";
import { describeError } from "../api/client";
import { createTask } from "../api/tasks";
import type { TaskPublic } from "../api/types";
import {
  CATEGORY_META,
  CATEGORY_ORDER,
  ENERGY_META,
  ENERGY_ORDER,
  TASK_TEMPLATES,
  TEMPLATE_PACKS,
  fitsEnergy,
  isTemplateOpen,
  openTaskTitles,
  templateById,
  templateToTaskCreate,
  type Energy,
  type TaskTemplate,
  type TemplateCategory,
} from "../taskTemplates";

const COLLAPSED_COUNT = 6;

interface PendingAdd {
  label: string;
  templates: TaskTemplate[];
}

/**
 * Adicionar missão sem escrever nada: um toque num cartão = missão
 * criada. Filtros por energia ("Tô sem energia") e por área. Pacotes
 * adicionam 3–4 de uma vez.
 *
 * O toque NÃO cria na hora: fica 3 s em "adicionando… Desfazer" e só
 * então chama `POST /tasks`. Toque errado é comum (e com TDAH, mais
 * ainda) — e como o backend não tem DELETE de tarefa, desfazer depois
 * de criada viraria um "cancelamento" contando nos padrões. Esperar
 * alguns segundos evita sujar os dados. Sair da tela confirma na hora.
 */
export function QuickAddTasks({
  tasks,
  onCreated,
  defaultEnergy = null,
  commitDelayMs = 3000,
}: {
  tasks: TaskPublic[] | null;
  onCreated: (task: TaskPublic) => void;
  defaultEnergy?: Energy | null;
  commitDelayMs?: number;
}) {
  const [energy, setEnergy] = useState<Energy | null>(defaultEnergy);
  const [category, setCategory] = useState<TemplateCategory | null>(null);
  const [pending, setPending] = useState<PendingAdd | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [justAdded, setJustAdded] = useState<string | null>(null);
  const [showAll, setShowAll] = useState(false);

  const pendingRef = useRef<PendingAdd | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const onCreatedRef = useRef(onCreated);
  useEffect(() => {
    onCreatedRef.current = onCreated;
  }, [onCreated]);

  const openTitles = useMemo(() => openTaskTitles(tasks), [tasks]);

  async function commit(batch: PendingAdd) {
    setError(null);
    try {
      for (const template of batch.templates) {
        const created = await createTask(templateToTaskCreate(template));
        onCreatedRef.current(created);
      }
      setJustAdded(batch.label);
    } catch (err) {
      setError(describeError(err, "não foi possível adicionar"));
    }
  }

  function flush() {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = null;
    const batch = pendingRef.current;
    pendingRef.current = null;
    setPending(null);
    if (batch) void commit(batch);
  }

  function queue(batch: PendingAdd) {
    // um novo toque confirma o anterior na hora — nunca perde nada
    if (pendingRef.current) flush();
    pendingRef.current = batch;
    setPending(batch);
    setJustAdded(null);
    timerRef.current = setTimeout(flush, commitDelayMs);
  }

  function undo() {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = null;
    pendingRef.current = null;
    setPending(null);
  }

  // sair da tela com algo pendente = confirma (a intenção foi adicionar)
  useEffect(() => () => flush(), []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!justAdded) return;
    const id = setTimeout(() => setJustAdded(null), 2500);
    return () => clearTimeout(id);
  }, [justAdded]);

  const visible = TASK_TEMPLATES.filter(
    (t) => fitsEnergy(t, energy) && (category === null || t.category === category),
  );
  // lista longa demais sobrecarrega: por padrão mostra só as primeiras
  const limited = !showAll && visible.length > COLLAPSED_COUNT;
  const shown = limited ? visible.slice(0, COLLAPSED_COUNT) : visible;
  const pendingIds = new Set(pending?.templates.map((t) => t.id) ?? []);

  function addPack(packId: string) {
    const pack = TEMPLATE_PACKS.find((p) => p.id === packId);
    if (!pack) return;
    const templates = pack.templateIds
      .map(templateById)
      .filter((t): t is TaskTemplate => !!t && !isTemplateOpen(t, openTitles));
    if (templates.length === 0) return;
    queue({ label: `${pack.title} (${templates.length})`, templates });
  }

  return (
    <section className="card quick-add" aria-labelledby="quick-add-title">
      <div className="quick-add__head">
        <h2 id="quick-add-title">Adicionar sem escrever</h2>
        <p className="checkin-hint">Toque no que você precisa fazer. Já vem com tempo e primeiro passo.</p>
      </div>

      <div className="chip-row" role="group" aria-label="Quanta energia você tem agora">
        {ENERGY_ORDER.map((e) => (
          <button
            key={e}
            type="button"
            className={`chip-option chip-option--energy-${e}${energy === e ? " chip-option--selected" : ""}`}
            aria-pressed={energy === e}
            onClick={() => setEnergy(energy === e ? null : e)}
          >
            {ENERGY_META[e].label}
          </button>
        ))}
      </div>

      <div className="quick-add__packs" role="group" aria-label="Pacotes prontos">
        {TEMPLATE_PACKS.map((pack) => {
          const remaining = pack.templateIds.filter((id) => {
            const t = templateById(id);
            return t && !isTemplateOpen(t, openTitles);
          }).length;
          return (
            <button
              key={pack.id}
              type="button"
              className="pack-card"
              onClick={() => addPack(pack.id)}
              disabled={remaining === 0}
            >
              <span className="pack-card__icon" aria-hidden="true">
                {pack.icon}
              </span>
              <span className="pack-card__text">
                <strong>{pack.title}</strong>
                <small>{remaining === 0 ? "tudo já na lista" : `${pack.hint} · ${remaining} itens`}</small>
              </span>
            </button>
          );
        })}
      </div>

      <div className="quick-add__tabs" role="tablist" aria-label="Áreas">
        <button
          type="button"
          role="tab"
          aria-selected={category === null}
          className={`tab-chip${category === null ? " tab-chip--active" : ""}`}
          onClick={() => { setCategory(null); setShowAll(false); }}
        >
          Tudo
        </button>
        {CATEGORY_ORDER.map((c) => (
          <button
            key={c}
            type="button"
            role="tab"
            aria-selected={category === c}
            className={`tab-chip${category === c ? " tab-chip--active" : ""}`}
            onClick={() => { setCategory(c); setShowAll(false); }}
          >
            <span aria-hidden="true">{CATEGORY_META[c].icon}</span> {CATEGORY_META[c].label}
          </button>
        ))}
      </div>

      <ul className="template-grid">
        {shown.map((t) => {
          const already = isTemplateOpen(t, openTitles);
          const isPending = pendingIds.has(t.id);
          return (
            <li key={t.id}>
              <button
                type="button"
                className={`template-tile template-tile--${t.energy}${isPending ? " template-tile--pending" : ""}`}
                onClick={() => queue({ label: t.title, templates: [t] })}
                disabled={already || isPending}
                aria-label={`${t.title}, ${t.minutes} minutos${already ? ", já está na lista" : ""}`}
              >
                <span className="template-tile__icon" aria-hidden="true">
                  {CATEGORY_META[t.category].icon}
                </span>
                <span className="template-tile__title">{t.title}</span>
                <span className="template-tile__meta">
                  {already ? "✓ na lista" : isPending ? "adicionando…" : `${t.minutes} min · ${ENERGY_META[t.energy].short}`}
                </span>
              </button>
            </li>
          );
        })}
      </ul>
      {limited && (
        <button type="button" className="button button--ghost button--small quick-add__more" onClick={() => setShowAll(true)}>
          Ver mais {visible.length - COLLAPSED_COUNT}
        </button>
      )}
      {visible.length === 0 && <p className="checkin-hint">nada nesse filtro — tente outra área.</p>}

      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}

      {(pending || justAdded) && (
        <div className="undo-toast" role="status">
          {pending ? (
            <>
              <span>
                Adicionando <strong>{pending.label}</strong>…
              </span>
              <button type="button" className="undo-toast__action" onClick={undo}>
                Desfazer
              </button>
              <button type="button" className="undo-toast__action" onClick={flush}>
                OK
              </button>
              <span className="undo-toast__bar" style={{ animationDuration: `${commitDelayMs}ms` }} />
            </>
          ) : (
            <span>
              ✓ <strong>{justAdded}</strong> na sua lista.
            </span>
          )}
        </div>
      )}
    </section>
  );
}
