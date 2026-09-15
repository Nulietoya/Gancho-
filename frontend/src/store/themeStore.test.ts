import { afterEach, expect, it } from "vitest";
import { useThemeStore } from "./themeStore";

afterEach(() => {
  localStorage.clear();
  delete document.documentElement.dataset.theme;
  useThemeStore.setState({ theme: "light" });
});

it("começa no tema claro por padrão quando não há nada salvo", () => {
  expect(useThemeStore.getState().theme).toBe("light");
  expect(document.documentElement.dataset.theme).toBeUndefined();
});

it("troca pro tema escuro, aplica no <html> e salva em localStorage", () => {
  useThemeStore.getState().setTheme("dark");

  expect(useThemeStore.getState().theme).toBe("dark");
  expect(document.documentElement.dataset.theme).toBe("dark");
  expect(localStorage.getItem("gancho_theme")).toBe("dark");
});

it("volta pro tema claro e remove o atributo do <html>", () => {
  useThemeStore.getState().setTheme("dark");
  useThemeStore.getState().setTheme("light");

  expect(useThemeStore.getState().theme).toBe("light");
  expect(document.documentElement.dataset.theme).toBeUndefined();
  expect(localStorage.getItem("gancho_theme")).toBe("light");
});
