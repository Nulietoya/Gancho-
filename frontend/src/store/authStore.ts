/**
 * Estado de autenticação (zustand, único store desta primeira leva —
 * decisão de escopo: cada tela busca seu próprio dado via `useEffect`
 * + `useState`, sem uma camada de cache de servidor tipo React Query
 * ainda; revisitar se/quando o número de telas fizer duplicação de
 * chamada virar problema de verdade).
 *
 * Access token vive só em memória (nunca em localStorage — reduz o
 * que um XSS conseguiria roubar de forma persistente); refresh token
 * vive em localStorage pra sobreviver a um F5, e é sempre ROTACIONADO
 * a cada uso (o backend invalida o anterior — `auth_service.
 * rotate_refresh_token`, ETAPA 6), então a cópia em `localStorage` é
 * atualizada em todo login/refresh.
 */
import { create } from "zustand";
import { ApiError, rawJson } from "../api/client";
import type { TokenPair, UserPublic } from "../api/types";

const REFRESH_TOKEN_KEY = "gancho_refresh_token";
let refreshInFlight: Promise<string | null> | null = null;

type AuthStatus = "idle" | "loading" | "authenticated" | "unauthenticated";

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  user: UserPublic | null;
  status: AuthStatus;
  error: string | null;
  initialize: () => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  /** Troca o refresh token por um par novo. Devolve o novo access token, ou `null` se a sessão não pôde ser renovada. */
  refresh: () => Promise<string | null>;
}

async function fetchMe(accessToken: string): Promise<UserPublic> {
  return rawJson<UserPublic>("/auth/me", {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
}

export const useAuthStore = create<AuthState>((set, get) => ({
  accessToken: null,
  refreshToken: null,
  user: null,
  status: "idle",
  error: null,

  initialize: async () => {
    const storedRefresh = localStorage.getItem(REFRESH_TOKEN_KEY);
    if (!storedRefresh) {
      set({ status: "unauthenticated" });
      return;
    }
    set({ status: "loading" });
    try {
      const tokens = await rawJson<TokenPair>("/auth/refresh", {
        method: "POST",
        body: JSON.stringify({ refresh_token: storedRefresh }),
      });
      const user = await fetchMe(tokens.access_token);
      localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
      set({
        accessToken: tokens.access_token,
        refreshToken: tokens.refresh_token,
        user,
        status: "authenticated",
        error: null,
      });
    } catch {
      localStorage.removeItem(REFRESH_TOKEN_KEY);
      set({ accessToken: null, refreshToken: null, user: null, status: "unauthenticated" });
    }
  },

  login: async (email, password) => {
    set({ status: "loading", error: null });
    try {
      const tokens = await rawJson<TokenPair>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      const user = await fetchMe(tokens.access_token);
      localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
      set({
        accessToken: tokens.access_token,
        refreshToken: tokens.refresh_token,
        user,
        status: "authenticated",
        error: null,
      });
    } catch (err) {
      set({ status: "unauthenticated", error: err instanceof ApiError ? err.detail : "não foi possível entrar" });
      throw err;
    }
  },

  register: async (email, password) => {
    set({ status: "loading", error: null });
    try {
      await rawJson<UserPublic>("/auth/register", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
    } catch (err) {
      set({ status: "unauthenticated", error: err instanceof ApiError ? err.detail : "não foi possível criar a conta" });
      throw err;
    }
    // Cadastro em si não devolve token (item 35 — v1 sem verificação de
    // e-mail, conta já ativa na hora) — login em seguida pra entrar
    // direto, sem pedir a senha de novo.
    await get().login(email, password);
  },

  logout: async () => {
    if (refreshInFlight) await refreshInFlight;
    const refreshToken = get().refreshToken;
    if (refreshToken) {
      try {
        await rawJson("/auth/logout", {
          method: "POST",
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
      } catch {
        // best-effort: mesmo se a chamada falhar (rede, token já
        // revogado), o estado local é limpo do mesmo jeito abaixo.
      }
    }
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    set({ accessToken: null, refreshToken: null, user: null, status: "unauthenticated", error: null });
  },

  refresh: () => {
    if (refreshInFlight) return refreshInFlight;
    refreshInFlight = (async () => {
      const refreshToken = get().refreshToken;
      if (!refreshToken) return null;
      try {
        const tokens = await rawJson<TokenPair>("/auth/refresh", {
          method: "POST",
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
        localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
        set({ accessToken: tokens.access_token, refreshToken: tokens.refresh_token });
        return tokens.access_token;
      } catch {
        localStorage.removeItem(REFRESH_TOKEN_KEY);
        set({ accessToken: null, refreshToken: null, user: null, status: "unauthenticated" });
        return null;
      }
    })();
    void refreshInFlight.finally(() => {
      refreshInFlight = null;
    });
    return refreshInFlight;
  },
}));

