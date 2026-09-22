import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createTask } from "../api/tasks";
import type { TaskPublic } from "../api/types";
import { QuickAddTasks } from "./QuickAddTasks";

vi.mock("../api/tasks", () => ({ createTask: vi.fn() }));

function created(title: string): TaskPublic {
  return { id: title, title, status: "pending" } as TaskPublic;
}

describe("QuickAddTasks — adicionar sem escrever", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.mocked(createTask).mockReset();
    vi.mocked(createTask).mockImplementation(async (data) => created(data.title));
  });
  afterEach(() => vi.useRealTimers());

  it("um toque cria a missão depois da janela de desfazer, com tempo e primeiro passo", async () => {
    const onCreated = vi.fn();
    render(<QuickAddTasks tasks={[]} onCreated={onCreated} commitDelayMs={1000} />);
    fireEvent.click(screen.getByRole("button", { name: /Beber um copo d'água/ }));
    expect(createTask).not.toHaveBeenCalled();
    expect(screen.getByRole("status")).toHaveTextContent(/Adicionando/);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000);
    });
    expect(createTask).toHaveBeenCalledWith(
      expect.objectContaining({ title: "Beber um copo d'água", category: "corpo", estimated_minutes: 2 }),
    );
    expect(onCreated).toHaveBeenCalledTimes(1);
  });

  it("Desfazer não chama a API (não suja os padrões com cancelamento)", async () => {
    render(<QuickAddTasks tasks={[]} onCreated={vi.fn()} commitDelayMs={1000} />);
    fireEvent.click(screen.getByRole("tab", { name: /Casa/ }));
    fireEvent.click(screen.getByRole("button", { name: /Tirar o lixo/ }));
    fireEvent.click(screen.getByRole("button", { name: "Desfazer" }));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000);
    });
    expect(createTask).not.toHaveBeenCalled();
  });

  it("pacote adiciona vários de uma vez, pulando o que já está na lista", async () => {
    const onCreated = vi.fn();
    render(
      <QuickAddTasks tasks={[created("Tirar o lixo")]} onCreated={onCreated} commitDelayMs={1000} />,
    );
    fireEvent.click(screen.getByRole("button", { name: /Casa em 15 min/ }));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000);
    });
    expect(createTask).toHaveBeenCalledTimes(2);
    expect(vi.mocked(createTask).mock.calls.map((c) => c[0].title)).not.toContain("Tirar o lixo");
  });

  it("mostra só 6 cartões de início; 'Ver mais' abre o resto", () => {
    render(<QuickAddTasks tasks={[]} onCreated={vi.fn()} />);
    expect(document.querySelectorAll(".template-tile")).toHaveLength(6);
    fireEvent.click(screen.getByRole("button", { name: /Ver mais/ }));
    expect(document.querySelectorAll(".template-tile").length).toBeGreaterThan(6);
  });

  it("filtro 'Tô sem energia' esconde tarefas pesadas", () => {
    render(<QuickAddTasks tasks={[]} onCreated={vi.fn()} />);
    fireEvent.click(screen.getByRole("tab", { name: /Trabalho/ }));
    expect(screen.getByRole("button", { name: /Bloco de foco de 25 minutos/ })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Tô sem energia" }));
    expect(screen.queryByRole("button", { name: /Bloco de foco de 25 minutos/ })).not.toBeInTheDocument();
  });

  it("tarefa já em aberto aparece marcada e desabilitada", () => {
    render(<QuickAddTasks tasks={[created("Arrumar a cama")]} onCreated={vi.fn()} />);
    fireEvent.click(screen.getByRole("tab", { name: /Casa/ }));
    expect(screen.getByRole("button", { name: /Arrumar a cama.*já está na lista/ })).toBeDisabled();
  });
});
