import { renderHook } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { useNow } from "./useNow";

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date("2026-09-16T09:30:00"));
});

afterEach(() => {
  vi.useRealTimers();
});

it("limpa o intervalo ao desmontar, sem deixar timer vivo pra trás", () => {
  const { unmount } = renderHook(() => useNow());
  const clearSpy = vi.spyOn(globalThis, "clearInterval");

  unmount();

  expect(clearSpy).toHaveBeenCalledTimes(1);
});
