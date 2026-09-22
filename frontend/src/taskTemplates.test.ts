import { describe, expect, it } from "vitest";
import type { TaskPublic } from "./api/types";
import {
  TASK_TEMPLATES,
  TEMPLATE_PACKS,
  energyFromFunctioning,
  openTaskTitles,
  suggestTemplates,
  templateById,
  templateToTaskCreate,
} from "./taskTemplates";

function task(title: string, status: TaskPublic["status"]): TaskPublic {
  return { title, status } as TaskPublic;
}

describe("catálogo de tarefas pré-prontas", () => {
  it("ids únicos e todo pacote aponta pra templates que existem", () => {
    const ids = TASK_TEMPLATES.map((t) => t.id);
    expect(new Set(ids).size).toBe(ids.length);
    for (const pack of TEMPLATE_PACKS) {
      for (const id of pack.templateIds) expect(templateById(id)).toBeDefined();
    }
  });

  it("respeita os limites do backend (título ≤200, categoria ≤80, minutos > 0)", () => {
    for (const t of TASK_TEMPLATES) {
      const payload = templateToTaskCreate(t);
      expect(payload.title.length).toBeLessThanOrEqual(200);
      expect((payload.category ?? "").length).toBeLessThanOrEqual(80);
      expect(payload.estimated_minutes).toBeGreaterThan(0);
      expect(payload.description).toBeTruthy();
    }
  });

  it("chip de funcionamento vira energia", () => {
    expect(energyFromFunctioning(1)).toBe("baixa");
    expect(energyFromFunctioning(2)).toBe("baixa");
    expect(energyFromFunctioning(4)).toBe("media");
    expect(energyFromFunctioning(5)).toBe("alta");
    expect(energyFromFunctioning(null)).toBeNull();
  });

  it("em dia travado só sugere coisa leve de até 5 min", () => {
    const list = suggestTemplates("baixa", new Set());
    expect(list.length).toBeGreaterThan(0);
    for (const t of list) {
      expect(t.energy).toBe("baixa");
      expect(t.minutes).toBeLessThanOrEqual(5);
    }
  });

  it("não sugere o que já está em aberto, mas sugere de novo o que já foi concluído", () => {
    const open = openTaskTitles([task("Beber um copo d'água", "pending"), task("Arrumar a cama", "completed")]);
    const titles = suggestTemplates(null, open).map((t) => t.title);
    expect(titles).not.toContain("Beber um copo d'água");
    expect(titles).toContain("Arrumar a cama");
  });

  it("'Outra' (seed) troca a primeira sugestão", () => {
    const a = suggestTemplates("media", new Set(), 0)[0];
    const b = suggestTemplates("media", new Set(), 1)[0];
    expect(a.id).not.toBe(b.id);
  });
});
