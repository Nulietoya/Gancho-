import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

/**
 * ETAPA 29: config separada de `vite.config.ts` (em vez de mesclar
 * um bloco `test` nele) porque `vite.config.ts` é lido também por
 * `tsc -b`/`vite build`, que não conhecem os tipos de `vitest/config`
 * — manter os dois arquivos separados evita qualquer risco de
 * quebrar o build de produção por causa de config de teste.
 */
export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    globals: false,
    css: false,
    // `e2e/*.spec.ts` usa `test`/`expect` de `@playwright/test`, não
    // de `vitest` — sem essa exclusão, o glob padrão do vitest
    // (`*.spec.ts`) tentava coletar esses arquivos e quebrava com
    // "did not expect test.describe() to be called here".
    exclude: ["**/node_modules/**", "e2e/**"],
  },
});
