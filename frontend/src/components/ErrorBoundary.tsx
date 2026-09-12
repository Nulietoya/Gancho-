import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
}

/**
 * ETAPA 28 (estado de erro): rede de segurança final — sem isto, um
 * erro de render em qualquer tela (ex.: um formato de resposta
 * inesperado do backend) derruba a aplicação inteira pra uma página
 * em branco, sem nenhuma explicação nem forma de se recuperar sem dar
 * F5 às cegas. `componentDidCatch` só existe como classe (React ainda
 * não tem equivalente em hook) — por isso é a única classe do
 * frontend. Deliberadamente não tenta "logar" o erro em lugar nenhum
 * (não há serviço de telemetria no MVP); só garante uma tela de saída
 * com um jeito de tentar de novo.
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // eslint-disable-next-line no-console
    console.error("Erro não tratado capturado pelo ErrorBoundary:", error, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-boundary">
          <h1>Algo deu errado</h1>
          <p>Essa tela encontrou um problema inesperado. Seus dados não foram perdidos.</p>
          <button type="button" className="button" onClick={() => window.location.reload()}>
            Recarregar
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
