import { useOnlineStatus } from "../hooks/useOnlineStatus";

/**
 * ETAPA 28: aviso proativo de offline — em vez de deixar a pessoa
 * descobrir que está sem conexão só quando uma ação falhar (e ler
 * `describeError`'s mensagem genérica de conexão em cada tela), este
 * banner aparece assim que o navegador perde a rede e some sozinho
 * quando ela volta. Não bloqueia nada: dados já carregados continuam
 * visíveis, só uma ação nova (fetch) vai falhar enquanto durar.
 */
export function OfflineBanner() {
  const online = useOnlineStatus();
  if (online) return null;
  return (
    <div className="offline-banner" role="status">
      Você está sem conexão com a internet. O que já estava na tela continua visível, mas ações novas só vão
      funcionar quando a conexão voltar.
    </div>
  );
}
