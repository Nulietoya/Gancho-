import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, describeError } from "./client";

/**
 * ETAPA 29: `describeError` é o ponto central de tradução de erro
 * criado na ETAPA 28 — se ele regredir, TODA tela volta a arriscar
 * mostrar "Failed to fetch" cru ou perder a mensagem do backend.
 * Vale o teste dedicado mesmo sendo uma função pequena.
 */
describe("describeError", () => {
  const originalOnLine = Object.getOwnPropertyDescriptor(navigator, "onLine");

  afterEach(() => {
    if (originalOnLine) {
      Object.defineProperty(navigator, "onLine", originalOnLine);
    }
    vi.restoreAllMocks();
  });

  function setOnline(value: boolean) {
    Object.defineProperty(navigator, "onLine", { configurable: true, value });
  }

  it("prioriza a mensagem do backend quando o erro é ApiError, mesmo offline", () => {
    setOnline(false);
    const err = new ApiError(404, "recurso não encontrado");
    expect(describeError(err, "fallback")).toBe("recurso não encontrado");
  });

  it("usa mensagem de conexão quando o navegador está offline", () => {
    setOnline(false);
    expect(describeError(new Error("qualquer coisa"), "fallback específico")).toMatch(/sem conexão/i);
  });

  it("usa mensagem de servidor quando é TypeError (fetch que não chegou a lugar nenhum) e está online", () => {
    setOnline(true);
    expect(describeError(new TypeError("Failed to fetch"), "fallback específico")).toMatch(/servidor/i);
  });

  it("cai no fallback específico da tela pra qualquer outro tipo de erro, online", () => {
    setOnline(true);
    expect(describeError(new Error("algo bem específico"), "fallback específico")).toBe("fallback específico");
  });

  it("nunca deixa 'Failed to fetch' cru chegar à tela", () => {
    setOnline(true);
    const message = describeError(new TypeError("Failed to fetch"), "fallback");
    expect(message.toLowerCase()).not.toContain("failed to fetch");
  });
});
