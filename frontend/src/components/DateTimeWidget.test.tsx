import { act, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { DateTimeWidget } from "./DateTimeWidget";

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date("2026-09-16T09:30:00"));
});

afterEach(() => {
  vi.useRealTimers();
});

it("mostra a data e a hora atuais, sem chamar nenhuma API", () => {
  render(<DateTimeWidget />);
  expect(screen.getByText(/16 de setembro de 2026/)).toBeInTheDocument();
  expect(screen.getByText("09:30:00")).toBeInTheDocument();
});

it("avança sozinho, sem precisar recarregar a página", () => {
  render(<DateTimeWidget />);
  expect(screen.getByText("09:30:00")).toBeInTheDocument();

  act(() => {
    vi.advanceTimersByTime(5000);
  });

  expect(screen.getByText("09:30:05")).toBeInTheDocument();
});
