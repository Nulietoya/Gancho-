import { afterEach, expect, it } from "vitest";
import { useThemeStore } from "./themeStore";

afterEach(() => {
  localStorage.clear();
  delete document.documentElement.dataset.theme;
  useThemeStore.setState({ theme: "dark" });
});

it("começa no tema escuro por padrão quando não há nada salvo", () => {
  expect(useThemeStore.getState().theme).toBe("dark");
});

it("troca pro tema claro, remove o atributo do <html> e salva em localStorage", () => {
  useThemeStore.getState().setTheme("light");

  expect(useThemeStore.getState().theme).toBe("light");
  expect(document.documentElement.dataset.theme).toBeUndefined();
  expect(localStorage.getItem("gancho_theme")).toBe("light");
});

it("volta pro tema escuro e aplica o atributo no <html>", () => {
  useThemeStore.getState().setTheme("light");
  useThemeStore.getState().setTheme("dark");

  expect(useThemeStore.getState().theme).toBe("dark");
  expect(document.documentElement.dataset.theme).toBe("dark");
  expect(localStorage.getItem("gancho_theme")).toBe("dark");
});
