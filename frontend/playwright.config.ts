import { defineConfig, devices } from "@playwright/test";

/**
 * ETAPA 29: suíte E2E COMMITADA — formaliza (não substitui, porque
 * continuam úteis pra explorar interativamente) os scripts Playwright
 * ad hoc que verificaram cada leva da ETAPA 27 durante a sessão.
 * Sem isso, a única garantia de que o frontend inteiro funciona de
 * ponta a ponta contra o backend real era rodar manualmente de novo
 * — o que, na prática, ninguém faz depois que a sessão termina.
 *
 * Pré-requisito (igual ao de rodar a aplicação manualmente, ver
 * README): Postgres do backend já rodando e `backend/.venv` já
 * criado com as dependências instaladas. `webServer` abaixo sobe
 * backend e frontend sozinho, contra esse Postgres.
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false, // specs compartilham o mesmo backend/banco — evita corrida entre eles
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: "http://localhost:5173",
    trace: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        // Em máquinas normais, `npx playwright install chromium` (uma
        // vez só) resolve o binário sozinho e esta variável fica sem
        // efeito. Ela só existe pra ambientes com um Chromium fixo já
        // pré-instalado num caminho não padrão (ex.: o sandbox usado
        // pra construir este projeto) e sem acesso pra baixar outro.
        launchOptions: process.env.PLAYWRIGHT_CHROMIUM_PATH
          ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_PATH }
          : {},
      },
    },
  ],
  webServer: [
    {
      command: "bash -c 'cd ../backend && source .venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000'",
      url: "http://localhost:8000/health",
      reuseExistingServer: true,
      timeout: 30_000,
    },
    {
      command: "npm run dev -- --host 0.0.0.0 --port 5173",
      url: "http://localhost:5173",
      reuseExistingServer: true,
      timeout: 30_000,
    },
  ],
});
