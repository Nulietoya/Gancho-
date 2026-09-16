import { useEffect, useState } from "react";

/**
 * Relógio de tempo real, sem nenhuma chamada de API — só o `Date`
 * do próprio navegador de quem está usando, atualizado a cada
 * segundo. Pedido explícito: "não o do Google, relógio com tempo
 * real" — nada de sincronizar com calendário externo nem servidor,
 * é só mostrar a hora local certa e deixá-la andando na tela.
 */
export function useNow(intervalMs = 1000): Date {
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), intervalMs);
    return () => clearInterval(id);
  }, [intervalMs]);

  return now;
}
