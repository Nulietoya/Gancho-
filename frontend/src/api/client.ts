/**
 * Camada mais baixa de acesso à API: monta a URL, injeta
 * `Content-Type`, e traduz uma resposta de erro do FastAPI (corpo
 * `{"detail": "..."}` ou `{"detail": [{"msg": "..."}]}` de erro de
 * validação do Pydantic) numa `ApiError` com mensagem pronta pra
 * mostrar na tela. Não sabe nada sobre token de autenticação — isso é
 * responsabilidade de `apiFetch.ts`, que usa este módulo por baixo
 * (evita import circular: este arquivo nunca importa a store de auth).
 */

const DEFAULT_BASE_URL = "http://localhost:8000/api/v1";

export const API_BASE_URL: string =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? DEFAULT_BASE_URL;

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

export async function parseErrorDetail(response: Response): Promise<string> {
  try {
    const body = await response.json();
    if (typeof body?.detail === "string") {
      return body.detail;
    }
    if (Array.isArray(body?.detail) && body.detail.length > 0) {
      return body.detail[0]?.msg ?? "requisição inválida";
    }
  } catch {
    // corpo vazio ou não-JSON (ex.: 204, ou erro de rede) — segue com mensagem genérica
  }
  return "algo deu errado, tente novamente";
}

/**
 * Traduz qualquer erro capturado num `catch` numa mensagem pronta pra
 * mostrar na tela — peça central da ETAPA 28 (loading/erro/vazio/
 * offline: nunca deixar "Failed to fetch" ou um erro cru chegar à
 * pessoa). Prioridade: erro de API já vem com mensagem do backend
 * (`ApiError.detail`); senão, se o navegador está sem conexão OU o
 * erro é o `TypeError` típico de um `fetch` que nunca chegou a um
 * servidor (rede caída, backend fora do ar), mensagem de conexão
 * genérica — mais útil que qualquer texto específico da tela, porque
 * o problema não é daquela tela; senão, a mensagem que a própria
 * chamada pediu como fallback.
 */
export function describeError(err: unknown, fallback: string): string {
  if (err instanceof ApiError) {
    return err.detail;
  }
  if (typeof navigator !== "undefined" && !navigator.onLine) {
    return "você está sem conexão com a internet — verifique e tente novamente";
  }
  if (err instanceof TypeError) {
    return "não foi possível falar com o servidor — tente novamente em instantes";
  }
  return fallback;
}

export async function rawFetch(path: string, options: RequestInit = {}): Promise<Response> {
  return fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });
}

/** Chamada sem token — usada só pelos endpoints públicos de auth (login/registro/refresh). */
export async function rawJson<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await rawFetch(path, options);
  if (!response.ok) {
    throw new ApiError(response.status, await parseErrorDetail(response));
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}
