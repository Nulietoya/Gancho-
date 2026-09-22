import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { createTask, startTask } from "../api/tasks";
import type { TaskPublic } from "../api/types";
import { SuggestNow } from "./SuggestNow";

vi.mock("../api/tasks", () => ({ createTask: vi.fn(), startTask: vi.fn() }));

describe("SuggestNow — 'me dá uma'", () => {
  it("'Fazer agora' cria e já inicia a missão num toque", async () => {
    vi.mocked(createTask).mockResolvedValue({ id: "n1", title: "x", status: "pending" } as TaskPublic);
    vi.mocked(startTask).mockResolvedValue({ id: "n1", title: "x", status: "started" } as TaskPublic);
    const onCreated = vi.fn();
    render(<SuggestNow tasks={[]} energy="baixa" onCreated={onCreated} />);
    fireEvent.click(screen.getByRole("button", { name: "Fazer agora" }));
    await waitFor(() => expect(onCreated).toHaveBeenCalledWith(expect.objectContaining({ status: "started" })));
    expect(startTask).toHaveBeenCalledWith("n1");
  });

  it("'Outra' troca a sugestão sem chamar a API", () => {
    render(<SuggestNow tasks={[]} energy={null} onCreated={vi.fn()} />);
    const before = document.querySelector(".suggest-now__title")?.textContent;
    fireEvent.click(screen.getByRole("button", { name: "Outra" }));
    expect(document.querySelector(".suggest-now__title")?.textContent).not.toBe(before);
    expect(createTask).not.toHaveBeenCalled();
  });
});
