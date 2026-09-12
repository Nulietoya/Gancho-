import { describe, expect, it } from "vitest";
import {
  ACTIVATION_DOMAIN_LABELS,
  ACTIVATION_DOMAIN_ORDER,
  INDICATOR_LABELS,
  INDICATOR_ORDER,
  OBSERVATION_CATEGORY_LABELS,
  OBSERVATION_CATEGORY_ORDER,
  OBSERVATION_INTENSITY_LABELS,
  OBSERVATION_INTENSITY_ORDER,
  OBSERVATION_SINCE_LABELS,
  OBSERVATION_SINCE_ORDER,
  PERMISSION_LABELS,
  PERMISSION_ORDER,
  PERSONAL_PLAN_SIGNAL_LABELS,
  PERSONAL_PLAN_SIGNAL_ORDER,
  TASK_FAILURE_REASON_LABELS,
  TASK_FAILURE_REASON_ORDER,
  TASK_PRIORITY_LABELS,
  TASK_PRIORITY_ORDER,
} from "./labels";

/**
 * ETAPA 29: `Record<Union, string>` já é conferido pelo `tsc -b` do
 * `npm run build` — se faltar uma chave, o build quebra sozinho. O
 * que o TypeScript NÃO confere é se um array `_ORDER` (usado pra
 * ordenar opção de `<select>`) continua cobrindo o mesmo conjunto: um
 * valor novo na union não obriga o array a ser atualizado, e ninguém
 * ia notar até abrir aquele formulário específico. Por isso o teste
 * aqui não é redundante com o build — é o único lugar que pega essa
 * classe de esquecimento.
 */
describe("toda lista _ORDER cobre exatamente as mesmas chaves do _LABELS correspondente", () => {
  const pairs: [string, Record<string, string>, string[]][] = [
    ["PERMISSION", PERMISSION_LABELS, PERMISSION_ORDER],
    ["INDICATOR", INDICATOR_LABELS, INDICATOR_ORDER],
    ["OBSERVATION_CATEGORY", OBSERVATION_CATEGORY_LABELS, OBSERVATION_CATEGORY_ORDER],
    ["OBSERVATION_SINCE", OBSERVATION_SINCE_LABELS, OBSERVATION_SINCE_ORDER],
    ["OBSERVATION_INTENSITY", OBSERVATION_INTENSITY_LABELS, OBSERVATION_INTENSITY_ORDER],
    ["ACTIVATION_DOMAIN", ACTIVATION_DOMAIN_LABELS, ACTIVATION_DOMAIN_ORDER],
    ["PERSONAL_PLAN_SIGNAL", PERSONAL_PLAN_SIGNAL_LABELS, PERSONAL_PLAN_SIGNAL_ORDER],
    ["TASK_PRIORITY", TASK_PRIORITY_LABELS, TASK_PRIORITY_ORDER],
    ["TASK_FAILURE_REASON", TASK_FAILURE_REASON_LABELS, TASK_FAILURE_REASON_ORDER],
  ];

  it.each(pairs)("%s", (_name, labels, order) => {
    const labelKeys = Object.keys(labels).sort();
    const orderKeys = [...order].sort();
    expect(orderKeys).toEqual(labelKeys);
    expect(new Set(order).size).toBe(order.length); // sem duplicata
  });
});
