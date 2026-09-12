import { useEffect, useState } from "react";

/**
 * ETAPA 28 (estados de offline): reflete `navigator.onLine` e reage a
 * `online`/`offline` do browser. Não é 100% preciso (o navegador só
 * sabe se a placa de rede está ligada, não se o backend responde),
 * mas cobre o caso comum — sem wifi/dados — e é o único sinal padrão
 * disponível sem sondar o servidor a cada poucos segundos.
 */
export function useOnlineStatus(): boolean {
  const [online, setOnline] = useState(() => (typeof navigator === "undefined" ? true : navigator.onLine));

  useEffect(() => {
    function handleOnline() {
      setOnline(true);
    }
    function handleOffline() {
      setOnline(false);
    }
    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);
    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  return online;
}
