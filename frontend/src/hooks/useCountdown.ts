import { useEffect, useState } from "react";

export interface Countdown {
  totalSeconds: number;
  remainingSeconds: number;
  running: boolean;
  start: () => void;
  pause: () => void;
  reset: (seconds: number) => void;
}

/**
 * Cronômetro regressivo simples, sem nenhuma chamada de API — só
 * `setInterval` no navegador de quem está usando (mesmo raciocínio de
 * `useNow`, que também não depende de conta nem permissão de
 * terceiro). Nada aqui é salvo em lugar nenhum: fechar a aba reseta o
 * timer, de propósito — não é um dado de produto, é uma ferramenta de
 * apoio momentâneo (ver `FocusTimer`).
 */
export function useCountdown(initialSeconds: number): Countdown {
  const [totalSeconds, setTotalSeconds] = useState(initialSeconds);
  const [remainingSeconds, setRemainingSeconds] = useState(initialSeconds);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    if (!running) return;
    const id = setInterval(() => {
      setRemainingSeconds((prev) => {
        if (prev <= 1) {
          setRunning(false);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(id);
  }, [running]);

  function start() {
    if (remainingSeconds > 0) setRunning(true);
  }

  function pause() {
    setRunning(false);
  }

  function reset(seconds: number) {
    setRunning(false);
    setTotalSeconds(seconds);
    setRemainingSeconds(seconds);
  }

  return { totalSeconds, remainingSeconds, running, start, pause, reset };
}
