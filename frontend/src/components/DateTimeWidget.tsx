import { useNow } from "../hooks/useNow";

/**
 * Cartão no topo do painel "Hoje" com a data de hoje e um relógio que
 * avança sozinho, a cada segundo — só o horário local do próprio
 * celular/computador de quem está usando, sem chamar nenhuma API
 * nem depender de conta ou permissão de terceiro (ver `useNow`).
 */
export function DateTimeWidget() {
  const now = useNow();

  // pt-BR devolve tudo minúsculo ("quarta-feira, 16 de setembro de
  // 2026") — maiúscula só a primeira letra, nunca cada palavra (por
  // isso não usar `text-transform: capitalize` no CSS, que capitalizaria
  // "De Setembro" também).
  const rawDate = now.toLocaleDateString("pt-BR", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });
  const date = rawDate.charAt(0).toUpperCase() + rawDate.slice(1);
  const time = now.toLocaleTimeString("pt-BR");

  return (
    <section className="card datetime-widget">
      <p className="datetime-widget__date">{date}</p>
      <p className="datetime-widget__time" aria-live="off">
        {time}
      </p>
    </section>
  );
}
