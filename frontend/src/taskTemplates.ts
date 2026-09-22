import type { TaskCreate, TaskPriority, TaskPublic } from "./api/types";

/**
 * Tarefas pré-prontas (2026-09) — pedido explícito: "escrever a tarefa é
 * pior que realizá-la". Pra quem tem TDAH, o custo de INICIAR (formular
 * a tarefa, decidir o tamanho, escolher prioridade) muitas vezes já é o
 * bloqueio inteiro. Aqui o catálogo faz esse trabalho: cada item já vem
 * com um tamanho pequeno, uma estimativa honesta de tempo e um
 * "primeiro passo" ridiculamente fácil (vai no campo `description`).
 *
 * Princípios usados na curadoria (os mesmos da pesquisa da ETAPA 37):
 * - quebrar em micro-passos reduz a barreira de iniciação;
 * - separar por ENERGIA disponível, não por importância — em dia ruim
 *   a pergunta útil é "o que eu consigo", não "o que eu devo";
 * - tempo explícito combate a cegueira temporal ("são só 5 min");
 * - corpo (água, comida, luz, sono) primeiro: é base de regulação.
 *
 * Tudo aqui é client-side: nenhuma tabela nova, nenhum endpoint novo.
 * A tarefa criada é uma tarefa normal (`POST /tasks`) com `category`
 * e `estimated_minutes` preenchidos — campos que já existiam no
 * backend e nunca eram usados pela UI.
 */

export type Energy = "baixa" | "media" | "alta";

export type TemplateCategory = "corpo" | "casa" | "foco" | "chatas" | "conexao" | "destravar";

export interface TaskTemplate {
  id: string;
  title: string;
  category: TemplateCategory;
  energy: Energy;
  minutes: number;
  firstStep: string;
  priority?: TaskPriority;
}

export interface TemplatePack {
  id: string;
  title: string;
  hint: string;
  icon: string;
  templateIds: string[];
}

export const CATEGORY_META: Record<TemplateCategory, { label: string; icon: string }> = {
  corpo: { label: "Corpo", icon: "💧" },
  casa: { label: "Casa", icon: "🏠" },
  foco: { label: "Trabalho/estudo", icon: "🎯" },
  chatas: { label: "Coisas chatas", icon: "📎" },
  conexao: { label: "Pessoas", icon: "💬" },
  destravar: { label: "Destravar", icon: "🔓" },
};

export const CATEGORY_ORDER: TemplateCategory[] = ["destravar", "corpo", "casa", "foco", "chatas", "conexao"];

export const ENERGY_META: Record<Energy, { label: string; short: string }> = {
  baixa: { label: "Tô sem energia", short: "leve" },
  media: { label: "Dá pra algo médio", short: "médio" },
  alta: { label: "Tô com gás", short: "pesado" },
};

export const ENERGY_ORDER: Energy[] = ["baixa", "media", "alta"];

export const TASK_TEMPLATES: TaskTemplate[] = [
  // destravar — pra quando nada sai do lugar
  { id: "levantar", title: "Levantar e mudar de cômodo", category: "destravar", energy: "baixa", minutes: 1, firstStep: "Só ficar de pé já conta." },
  { id: "respirar", title: "Respirar devagar por 1 minuto", category: "destravar", energy: "baixa", minutes: 1, firstStep: "Solta o ar primeiro, bem devagar." },
  { id: "musica", title: "Pôr uma música e começar qualquer coisa", category: "destravar", energy: "baixa", minutes: 3, firstStep: "Escolhe a música — o resto vem depois." },
  { id: "uma-coisa", title: "Escolher só UMA coisa pra hoje", category: "destravar", energy: "baixa", minutes: 2, firstStep: "Não precisa ser a mais importante, só uma." },
  { id: "celular-longe", title: "Deixar o celular em outro cômodo por 15 min", category: "destravar", energy: "media", minutes: 15, firstStep: "Leva ele até a porta do outro cômodo." },

  // corpo — base de regulação
  { id: "agua", title: "Beber um copo d'água", category: "corpo", energy: "baixa", minutes: 2, firstStep: "Pega o copo mais perto de você." },
  { id: "comer", title: "Comer alguma coisa", category: "corpo", energy: "baixa", minutes: 10, firstStep: "Qualquer coisa pronta vale. Não precisa cozinhar.", priority: "high" },
  { id: "dentes", title: "Escovar os dentes", category: "corpo", energy: "baixa", minutes: 3, firstStep: "Só colocar a pasta na escova." },
  { id: "sol", title: "5 minutos de luz do dia", category: "corpo", energy: "baixa", minutes: 5, firstStep: "Abre a janela ou a porta." },
  { id: "alongar", title: "Alongar o corpo por 3 minutos", category: "corpo", energy: "baixa", minutes: 3, firstStep: "Braços pra cima, uma vez." },
  { id: "banho", title: "Tomar banho", category: "corpo", energy: "media", minutes: 15, firstStep: "Só ligar o chuveiro." },
  { id: "caminhar", title: "Caminhada curta", category: "corpo", energy: "media", minutes: 15, firstStep: "Calçar o tênis. Só isso por enquanto." },
  { id: "dormir", title: "Começar a desligar pra dormir", category: "corpo", energy: "baixa", minutes: 10, firstStep: "Diminui a luz do quarto." },

  // casa — versão mínima, sem perfeccionismo
  { id: "cinco-coisas", title: "Guardar 5 coisas do lugar", category: "casa", energy: "baixa", minutes: 5, firstStep: "Só 5. Depois pode parar." },
  { id: "cama", title: "Arrumar a cama", category: "casa", energy: "baixa", minutes: 2, firstStep: "Puxa o lençol pra cima." },
  { id: "lixo", title: "Tirar o lixo", category: "casa", energy: "baixa", minutes: 3, firstStep: "Fecha o saco." },
  { id: "superficie", title: "Limpar uma superfície só", category: "casa", energy: "baixa", minutes: 5, firstStep: "Escolhe: mesa, pia ou escrivaninha." },
  { id: "roupa", title: "Pôr roupa pra lavar", category: "casa", energy: "media", minutes: 5, firstStep: "Junta as roupas num canto só." },
  { id: "louca", title: "Lavar a louça", category: "casa", energy: "media", minutes: 15, firstStep: "Lava só os copos primeiro." },
  { id: "mercado", title: "Fazer a lista do mercado", category: "casa", energy: "media", minutes: 5, firstStep: "Abre a geladeira e anota o que falta." },

  // foco — começar é a parte difícil
  { id: "abrir-arquivo", title: "Abrir o arquivo e ler a 1ª linha", category: "foco", energy: "baixa", minutes: 2, firstStep: "Só abrir. Não precisa fazer mais nada." },
  { id: "tres-passos", title: "Listar os próximos 3 passos", category: "foco", energy: "media", minutes: 5, firstStep: "O primeiro passo pode ser bobo." },
  { id: "frases-ruins", title: "Escrever 3 frases ruins", category: "foco", energy: "media", minutes: 10, firstStep: "Rascunho feio é permitido — melhora depois." },
  { id: "estudar-15", title: "Estudar 15 minutos", category: "foco", energy: "media", minutes: 15, firstStep: "Abre o material na página certa." },
  { id: "mesa", title: "Organizar a mesa de trabalho", category: "foco", energy: "media", minutes: 10, firstStep: "Tira da mesa só o que é lixo." },
  { id: "foco-25", title: "Bloco de foco de 25 minutos", category: "foco", energy: "alta", minutes: 25, firstStep: "Fecha as abas que não são disso.", priority: "high" },

  // coisas chatas — adiadas por aversão, não por dificuldade
  { id: "responder-1", title: "Responder 1 mensagem pendente", category: "chatas", energy: "media", minutes: 5, firstStep: "Começa pela mais fácil." },
  { id: "emails", title: "Olhar os e-mails não lidos", category: "chatas", energy: "media", minutes: 5, firstStep: "Só abrir a caixa de entrada." },
  { id: "conta", title: "Pagar uma conta", category: "chatas", energy: "media", minutes: 10, firstStep: "Abrir o app do banco.", priority: "high" },
  { id: "documentos", title: "Separar documentos/papéis", category: "chatas", energy: "media", minutes: 15, firstStep: "Faz uma pilha só, sem classificar ainda." },
  { id: "consulta", title: "Marcar uma consulta", category: "chatas", energy: "alta", minutes: 10, firstStep: "Achar o número ou o site já vale.", priority: "high" },
  { id: "ligacao", title: "Fazer a ligação que estou adiando", category: "chatas", energy: "alta", minutes: 10, firstStep: "Escreve num papel a primeira frase que vai dizer." },

  // pessoas — conexão e apoio (body doubling)
  { id: "mensagem-querida", title: "Mandar mensagem pra alguém querido", category: "conexao", energy: "baixa", minutes: 3, firstStep: "Um \"oi, lembrei de você\" basta." },
  { id: "avisar-confianca", title: "Contar pra alguém de confiança como estou", category: "conexao", energy: "baixa", minutes: 3, firstStep: "Pode ser uma palavra só." },
  { id: "body-doubling", title: "Chamar alguém pra ficar junto enquanto faço algo", category: "conexao", energy: "media", minutes: 5, firstStep: "Pergunta: \"topa ficar em chamada comigo 20 min?\"" },
];

export const TEMPLATE_PACKS: TemplatePack[] = [
  {
    id: "dia-pesado",
    title: "Dia pesado",
    hint: "o mínimo pra cuidar de você",
    icon: "🌧️",
    templateIds: ["agua", "comer", "avisar-confianca", "sol"],
  },
  {
    id: "manha",
    title: "Manhã mínima",
    hint: "começar o dia sem pensar",
    icon: "🌅",
    templateIds: ["agua", "dentes", "cama", "comer"],
  },
  {
    id: "casa-15",
    title: "Casa em 15 min",
    hint: "sem faxina, só respiro",
    icon: "🧺",
    templateIds: ["lixo", "cinco-coisas", "superficie"],
  },
  {
    id: "destravar-trabalho",
    title: "Destravar o trabalho",
    hint: "do zero ao foco em 3 passos",
    icon: "🚀",
    templateIds: ["celular-longe", "abrir-arquivo", "tres-passos", "foco-25"],
  },
];

const TEMPLATES_BY_ID = new Map(TASK_TEMPLATES.map((t) => [t.id, t]));

export function templateById(id: string): TaskTemplate | undefined {
  return TEMPLATES_BY_ID.get(id);
}

export function templateToTaskCreate(template: TaskTemplate): TaskCreate {
  return {
    title: template.title,
    description: template.firstStep,
    category: template.category,
    priority: template.priority ?? "medium",
    estimated_minutes: template.minutes,
    due_date: null,
  };
}

/** Ícone de uma tarefa já criada — só as que vieram do catálogo têm categoria conhecida. */
export function taskIcon(task: Pick<TaskPublic, "category">): string | null {
  if (!task.category) return null;
  return (CATEGORY_META as Record<string, { icon: string } | undefined>)[task.category]?.icon ?? null;
}

function normalize(title: string): string {
  return title.trim().toLocaleLowerCase("pt-BR");
}

/** Títulos de tarefas ainda em aberto — usado pra não sugerir/duplicar o que já está na lista. */
export function openTaskTitles(tasks: TaskPublic[] | null): Set<string> {
  const titles = new Set<string>();
  for (const t of tasks ?? []) {
    if (t.status !== "completed" && t.status !== "cancelled") titles.add(normalize(t.title));
  }
  return titles;
}

/** Abertos + concluídos hoje — pra "Me dá uma" não repetir o que você acabou de fazer. */
export function busyTaskTitles(tasks: TaskPublic[] | null): Set<string> {
  const titles = openTaskTitles(tasks);
  const today = new Date().toDateString();
  for (const t of tasks ?? []) {
    if (t.status === "completed" && t.completed_at && new Date(t.completed_at).toDateString() === today) {
      titles.add(normalize(t.title));
    }
  }
  return titles;
}

export function isTemplateOpen(template: TaskTemplate, openTitles: Set<string>): boolean {
  return openTitles.has(normalize(template.title));
}

/**
 * Traduz o chip "Como você está funcionando" da Home (1/2/4/5 em
 * `sense_of_functioning`) pra energia disponível. Sem check-in → null
 * (a UI mostra tudo).
 */
export function energyFromFunctioning(value: number | null | undefined): Energy | null {
  if (value == null) return null;
  if (value <= 2) return "baixa";
  if (value === 3 || value === 4) return "media";
  return "alta";
}

const ENERGY_RANK: Record<Energy, number> = { baixa: 0, media: 1, alta: 2 };

/** Cabe na energia de agora = pede no máximo essa energia (dia "médio" também aceita coisa leve). */
export function fitsEnergy(template: TaskTemplate, energy: Energy | null): boolean {
  if (energy === null) return true;
  return ENERGY_RANK[template.energy] <= ENERGY_RANK[energy];
}

/**
 * Sugestões pra "Me dá uma": tarefas que cabem na energia de agora e
 * ainda não estão na lista. Em dia travado, só coisas de até 5 min.
 * A ordem é embaralhada de forma determinística por `seed` (o botão
 * "Outra" só incrementa o seed) — assim o teste consegue prever.
 */
export function suggestTemplates(energy: Energy | null, openTitles: Set<string>, seed = 0): TaskTemplate[] {
  const pool = TASK_TEMPLATES.filter(
    (t) =>
      fitsEnergy(t, energy) &&
      !isTemplateOpen(t, openTitles) &&
      (energy !== "baixa" || t.minutes <= 5),
  );
  if (pool.length === 0) return [];
  const offset = ((seed % pool.length) + pool.length) % pool.length;
  return [...pool.slice(offset), ...pool.slice(0, offset)];
}
