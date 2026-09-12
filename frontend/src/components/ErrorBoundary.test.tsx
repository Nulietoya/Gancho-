import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ErrorBoundary } from "./ErrorBoundary";

function Boom(): never {
  throw new Error("boom de teste");
}

describe("ErrorBoundary", () => {
  it("renderiza os filhos normalmente quando não há erro", () => {
    render(
      <ErrorBoundary>
        <p>conteúdo normal</p>
      </ErrorBoundary>,
    );
    expect(screen.getByText("conteúdo normal")).toBeInTheDocument();
  });

  it("mostra a tela de fallback com botão de recarregar em vez de branco, quando um filho lança", () => {
    // React loga o erro de render no console por padrão — silenciado
    // só neste teste, pra não poluir a saída com um erro esperado.
    const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    render(
      <ErrorBoundary>
        <Boom />
      </ErrorBoundary>,
    );

    expect(screen.getByText("Algo deu errado")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Recarregar" })).toBeInTheDocument();

    consoleSpy.mockRestore();
  });
});
