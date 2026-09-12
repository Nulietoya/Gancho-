import { StrictMode, useEffect, useRef } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { App } from "./App";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { useAuthStore } from "./store/authStore";
import "./index.css";

function Root() {
  const initialize = useAuthStore((s) => s.initialize);
  // Guarda contra o duplo-efeito do StrictMode em dev: sem isso, dois
  // `initialize()` concorrentes disparam dois `/auth/refresh` com o
  // MESMO refresh token — o backend rotaciona o token a cada uso
  // (`auth_service.rotate_refresh_token`), então o segundo chegaria
  // com um token já invalidado pelo primeiro e derrubaria a sessão
  // por engano.
  const didInit = useRef(false);

  useEffect(() => {
    if (didInit.current) return;
    didInit.current = true;
    void initialize();
  }, [initialize]);

  return (
    <BrowserRouter>
      <ErrorBoundary>
        <App />
      </ErrorBoundary>
    </BrowserRouter>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Root />
  </StrictMode>,
);
