/**
 * Wrapper autenticado por cima de `client.ts`: injeta o access token
 * atual da store e, se a resposta vier 401 (token expirado — vida
 * curta de 15min, item 36), tenta renovar UMA vez via refresh token e
 * repete a chamada original antes de desistir. Módulo separado de
 * `client.ts` de propósito, pra `client.ts` nunca precisar importar a
 * store de auth (evita ciclo de import: authStore → client, e
 * apiFetch → client + authStore).
 */
import { ApiError, parseErrorDetail, rawFetch } from "./client";
import { useAuthStore } from "../store/authStore";

function withAuthHeader(options: RequestInit, token: string | null): RequestInit {
  return {
    ...options,
    headers: {
      ...options.headers,
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  };
}

export async function apiJson<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = useAuthStore.getState().accessToken;
  let response = await rawFetch(path, withAuthHeader(options, token));

  if (response.status === 401 && token) {
    const newToken = await useAuthStore.getState().refresh();
    if (newToken) {
      response = await rawFetch(path, withAuthHeader(options, newToken));
    }
  }

  if (!response.ok) {
    throw new ApiError(response.status, await parseErrorDetail(response));
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}
