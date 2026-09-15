/**
 * Tema visual (claro "calmo" — padrão — ou escuro), escolhido pela
 * pessoa em Configurações. Guardado em localStorage (não é dado de
 * conta, não precisa ir pro backend) e aplicado via
 * `document.documentElement.dataset.theme`, que é o seletor que
 * `index.css` usa pra trocar as variáveis de cor (`--color-*`).
 *
 * `index.html` tem um script inline que lê a mesma chave antes do
 * React montar, pra evitar o flash do tema claro em quem já escolheu
 * o escuro.
 */
import { create } from "zustand";

const THEME_KEY = "gancho_theme";

export type Theme = "light" | "dark";

function applyTheme(theme: Theme) {
  if (theme === "dark") {
    document.documentElement.dataset.theme = "dark";
  } else {
    delete document.documentElement.dataset.theme;
  }
}

function readStoredTheme(): Theme {
  try {
    return localStorage.getItem(THEME_KEY) === "dark" ? "dark" : "light";
  } catch {
    return "light";
  }
}

interface ThemeState {
  theme: Theme;
  setTheme: (theme: Theme) => void;
}

export const useThemeStore = create<ThemeState>((set) => ({
  theme: readStoredTheme(),
  setTheme: (theme) => {
    try {
      localStorage.setItem(THEME_KEY, theme);
    } catch {
      // localStorage indisponível — o tema ainda muda na tela, só não sobrevive a um F5.
    }
    applyTheme(theme);
    set({ theme });
  },
}));

// Garante que o atributo no <html> reflita o estado inicial mesmo se
// o script inline do index.html não puder rodar (ex.: testes em
// jsdom, que não carregam index.html).
applyTheme(useThemeStore.getState().theme);
