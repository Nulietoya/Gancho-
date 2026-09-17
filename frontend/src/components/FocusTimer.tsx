import { useState } from "react";
import { useCountdown } from "../hooks/useCountdown";

const PRESET_MINUTES = [5, 10, 15, 25];
const RADIUS = 54;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

function formatMinutesSeconds(totalSeconds: number): string {
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

/**
 * Timer visual pra cegueira temporal — independente do body doubling
 * (ETAPA 21): não pede nada a ninguém, não fica gravado em lugar
 * nenhum (nem em `localStorage`), só ajuda a ENXERGAR o tempo passando
 * enquanto se trabalha em algo. O disco (SVG) encolhendo é o ponto: um
 * número sozinho ("12:34 restantes") é fácil de dissociar de "quanto
 * tempo é isso de verdade" pra quem tem TDAH — ver a fatia diminuindo
 * é o mecanismo que timers visuais físicos (tipo Time Timer) usam pra
 * tornar o tempo concreto, e é o que este componente reproduz na tela.
 */
export function FocusTimer() {
  const [presetMinutes, setPresetMinutes] = useState(PRESET_MINUTES[0]);
  const { totalSeconds, remainingSeconds, running, start, pause, reset } = useCountdown(
    PRESET_MINUTES[0] * 60,
  );

  const fraction = totalSeconds > 0 ? remainingSeconds / totalSeconds : 0;
  const dashoffset = CIRCUMFERENCE * (1 - fraction);
  const justFinished = totalSeconds > 0 && remainingSeconds === 0;

  function choosePreset(minutes: number) {
    setPresetMinutes(minutes);
    reset(minutes * 60);
  }

  return (
    <section className="card focus-timer">
      <h2>Timer visual</h2>
      <p className="checkin-hint">
        Pra quando o tempo "some" enquanto você trabalha em algo — sem cobrança, sem ninguém vendo. Fica só
        nesta aba; fechar ou recarregar reinicia.
      </p>

      <div className="focus-timer__presets">
        {PRESET_MINUTES.map((minutes) => (
          <button
            key={minutes}
            type="button"
            className={`button button--ghost${presetMinutes === minutes ? " focus-timer__preset--active" : ""}`}
            onClick={() => choosePreset(minutes)}
          >
            {minutes} min
          </button>
        ))}
      </div>

      <div className="focus-timer__dial">
        <svg
          viewBox="0 0 120 120"
          width="140"
          height="140"
          role="img"
          aria-label={`${formatMinutesSeconds(remainingSeconds)} restantes`}
        >
          <circle cx="60" cy="60" r={RADIUS} className="focus-timer__track" />
          <circle
            cx="60"
            cy="60"
            r={RADIUS}
            className="focus-timer__progress"
            strokeDasharray={CIRCUMFERENCE}
            strokeDashoffset={dashoffset}
            transform="rotate(-90 60 60)"
          />
        </svg>
        <span className="focus-timer__time" aria-live="off">
          {formatMinutesSeconds(remainingSeconds)}
        </span>
      </div>

      {justFinished && (
        <p className="focus-timer__done" role="status">
          Tempo acabou.
        </p>
      )}

      <div className="relationship-card__actions">
        {!running ? (
          <button type="button" className="button" onClick={start} disabled={remainingSeconds === 0}>
            {remainingSeconds === totalSeconds ? "Começar" : "Continuar"}
          </button>
        ) : (
          <button type="button" className="button button--ghost" onClick={pause}>
            Pausar
          </button>
        )}
        <button type="button" className="button button--ghost" onClick={() => reset(presetMinutes * 60)}>
          Reiniciar
        </button>
      </div>
    </section>
  );
}
