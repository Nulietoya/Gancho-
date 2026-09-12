import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { TaskPublic, TaskStatus } from "../api/types";
import { TaskCard } from "./TasksPage";

// api/tasks faz chamadas de rede reais — mockado pra este teste olhar
// só a UI (quais botões aparecem por status), não o fetch em si.
vi.mock("../api/tasks", () => ({
  startTask: vi.fn(),
  resumeTask: vi.fn(),
  pauseTask: vi.fn(),
  postponeTask: vi.fn(),
  completeTask: vi.fn(),
  cancelTask: vi.fn(),
}));

function makeTask(status: TaskStatus): TaskPublic {
  return {
    id: "t1",
    title: "tarefa de teste",
    description: null,
    category: null,
    priority: "medium",
    status,
    due_date: null,
    estimated_minutes: null,
    actual_minutes: null,
    started_at: null,
    completed_at: null,
    postponed_count: 0,
    attempt_count: 0,
    origin: "self",
    source_relationship_id: null,
    support_relationship_id: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  };
}

function buttonNames(): string[] {
  return screen.queryAllByRole("button").map((b) => b.textContent ?? "");
}

/**
 * ETAPA 29: o mapa de transições válidas da máquina de estados vive
 * só no backend (`task_service.py`) — a UI não reimplementa a regra,
 * só decide QUANDO mostrar cada botão (comentário explícito no código
 * desde a ETAPA 27, 8ª leva). Esse "quando mostrar" é lógica de
 * frontend de verdade e pode regredir sem que nenhum teste de backend
 * perceba — por isso o teste aqui, por status.
 */
describe("TaskCard — botões de ação visíveis por status", () => {
  it("pending: Iniciar, Adiar, Concluir, Cancelar — nunca Retomar/Pausar", () => {
    render(<TaskCard task={makeTask("pending")} relationshipLabel={null} onChanged={vi.fn()} />);
    const names = buttonNames();
    expect(names).toEqual(expect.arrayContaining(["Iniciar", "Adiar", "Concluir", "Cancelar tarefa"]));
    expect(names).not.toContain("Retomar");
    expect(names).not.toContain("Pausar");
  });

  it("started: Pausar, Adiar, Concluir, Cancelar — nunca Iniciar/Retomar", () => {
    render(<TaskCard task={makeTask("started")} relationshipLabel={null} onChanged={vi.fn()} />);
    const names = buttonNames();
    expect(names).toEqual(expect.arrayContaining(["Pausar", "Adiar", "Concluir", "Cancelar tarefa"]));
    expect(names).not.toContain("Iniciar");
    expect(names).not.toContain("Retomar");
  });

  it("paused: Retomar, Adiar, Concluir, Cancelar — nunca Iniciar/Pausar", () => {
    render(<TaskCard task={makeTask("paused")} relationshipLabel={null} onChanged={vi.fn()} />);
    const names = buttonNames();
    expect(names).toEqual(expect.arrayContaining(["Retomar", "Adiar", "Concluir", "Cancelar tarefa"]));
    expect(names).not.toContain("Iniciar");
    expect(names).not.toContain("Pausar");
  });

  it("postponed: Iniciar disponível de novo (mesmo grupo de pending), nunca Retomar/Pausar", () => {
    render(<TaskCard task={makeTask("postponed")} relationshipLabel={null} onChanged={vi.fn()} />);
    const names = buttonNames();
    expect(names).toContain("Iniciar");
    expect(names).not.toContain("Retomar");
    expect(names).not.toContain("Pausar");
  });

  it("completed e cancelled são terminais — nenhum botão de ação, nenhum formulário de adiar", () => {
    render(<TaskCard task={makeTask("completed")} relationshipLabel={null} onChanged={vi.fn()} />);
    expect(buttonNames()).toEqual([]);

    render(<TaskCard task={makeTask("cancelled")} relationshipLabel={null} onChanged={vi.fn()} />);
    expect(buttonNames()).toEqual([]);
  });

  it("tarefa sugerida por pessoa de confiança mostra o rótulo do relacionamento", () => {
    render(<TaskCard task={{ ...makeTask("pending"), origin: "trusted_person_suggestion" }} relationshipLabel="Maria" onChanged={vi.fn()} />);
    expect(screen.getByText(/sugerida por Maria/i)).toBeInTheDocument();
  });
});
