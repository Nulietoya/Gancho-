import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

// Desmonta o componente renderizado depois de cada teste — sem isso,
// o DOM de um teste vaza pro próximo (Testing Library não faz isso
// sozinho fora de um ambiente que já injeta esse hook, ex. Jest com
// jest-environment).
afterEach(() => {
  cleanup();
});
