import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { FocusTimer } from "./FocusTimer";

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

it("começa no preset padrão (5 min), parado", () => {
  render(<FocusTimer />);
  expect(screen.getByText("05:00")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Começar" })).toBeInTheDocument();
});

it("conta regressivamente depois de começar, sem chamar nenhuma API", () => {
  render(<FocusTimer />);
  fireEvent.click(screen.getByRole("button", { name: "Começar" }));

  act(() => {
    vi.advanceTimersByTime(3000);
  });

  expect(screen.getByText("04:57")).toBeInTheDocument();
});

it("pausa e reinicia sem perder nem resetar o tempo errado", () => {
  render(<FocusTimer />);
  fireEvent.click(screen.getByRole("button", { name: "Começar" }));
  act(() => {
    vi.advanceTimersByTime(2000);
  });
  fireEvent.click(screen.getByRole("button", { name: "Pausar" }));
  act(() => {
    vi.advanceTimersByTime(5000); // pausado — não deveria mudar
  });
  expect(screen.getByText("04:58")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "Reiniciar" }));
  expect(screen.getByText("05:00")).toBeInTheDocument();
});

it("troca de preset reinicia o tempo pro novo valor", () => {
  render(<FocusTimer />);
  fireEvent.click(screen.getByRole("button", { name: "25 min" }));
  expect(screen.getByText("25:00")).toBeInTheDocument();
});

it("mostra 'tempo acabou' quando chega a zero", () => {
  render(<FocusTimer />);
  fireEvent.click(screen.getByRole("button", { name: "5 min" }));
  fireEvent.click(screen.getByRole("button", { name: "Começar" }));
  act(() => {
    vi.advanceTimersByTime(5 * 60 * 1000);
  });
  expect(screen.getByText("00:00")).toBeInTheDocument();
  expect(screen.getByText("Tempo acabou.")).toBeInTheDocument();
});
