import { create } from "zustand";

/**
 * Reforço imediato ao concluir uma missão. Com TDAH a recompensa
 * precisa ser AGORA (não "no fim da semana no gráfico") — por isso um
 * toast curto e visível no momento do "Concluir", em qualquer tela.
 * Frases sóbrias de propósito: reconhecem o feito sem tom infantil.
 * Nada é salvo: é só feedback de interface.
 */
const PHRASES = [
  "Feito. Isso conta.",
  "Mais uma fora da cabeça.",
  "Você começou e terminou. Isso é o difícil.",
  "Pronto. Pode respirar.",
  "Uma a menos. Bom trabalho.",
];

interface CelebrationState {
  message: string | null;
  detail: string | null;
  key: number;
  celebrate: (detail: string) => void;
  dismiss: () => void;
}

export const useCelebrationStore = create<CelebrationState>((set, get) => ({
  message: null,
  detail: null,
  key: 0,
  celebrate: (detail) => {
    const key = get().key + 1;
    set({ message: PHRASES[key % PHRASES.length], detail, key });
  },
  dismiss: () => set({ message: null, detail: null }),
}));
