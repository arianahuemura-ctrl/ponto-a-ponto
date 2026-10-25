# Consentimento voluntário de pesquisa

## Contratos definidos antes da implementação

- `GET /api/research/info/`: informação pública da pesquisa, contato configurável e token CSRF; não cria sessão de pesquisa nem abre o banco de telemetria.
- `POST /api/research/feedback/`: JSON `{id, category, message, token?}`. ID UUID de idempotência, categoria problema/sugestao/elogio, mensagem de 1–2000 caracteres. Token opcional vincula uma sessão já existente; omiti-lo registra somente o relato voluntário. Nunca inicia replay. Retorna 201 `{receipt, linked}`; repetição idêntica retorna 200. CSRF obrigatório.
- `POST /api/research/requests/`: JSON `{id, kind, message, proofs}`. kind contact/deletion; até 50 comprovantes assinados de sessões deste navegador, mensagem até 2000 caracteres. Recebe solicitação para análise administrativa, sem prometer exclusão imediata. Retorna 201 `{receipt}`; repetição idêntica retorna 200. CSRF obrigatório. Não aceita identificadores de sessão sem comprovante.
- Erros desses POSTs: 400 entrada inválida; 403 CSRF; 409 reutilização de ID com conteúdo diferente; 429 limite de solicitações; 503 armazenamento indisponível/cheio. Conteúdo não é refletido em erros. Relatos e solicitações ficam em banco separado, restrito à administração.
- `GET /api/usability/`: preserva contrato existente e acrescenta comprovante assinado para solicitar exclusão posteriormente. Só é solicitado pelo cliente após aceitar a pesquisa. O comprovante não autoriza ler nem apagar dados.

## Limites de retenção atuais

Não será executada limpeza de dados reais nesta tarefa. A implementação existente elimina eventos com mais de 30 dias quando recebe uma nova gravação; blocos de sessões ainda existentes e exportações podem permanecer. O aviso deve descrever esse critério, sem garantir exclusão completa em 30 dias. Relatos voluntários e solicitações terão tratamento administrativo e informação explícita sobre a ausência de limpeza automática. Cópias baixadas exigem tratamento pelos responsáveis.

## Política da escolha

Escolha aceita ou recusada, versão do aviso e instante ficam em chave própria no armazenamento local. Não há expiração temporal inventada. Mudanças relevantes de finalidade, categorias coletadas, acesso ou retenção exigem atualizar a versão e solicitar novamente a escolha. Falha ou ausência de armazenamento não significa aceite. A sessão de pesquisa é independente da escolha.


## Comportamento anterior e correção de 23/10/2026

Antes, só o estado de pesquisa ativa renderizava a aplicação. A aceitação dependia da criação da sessão e do primeiro envio; recusar ou falhar a gravação impedia o acesso ao transporte. A escolha não era persistida, listeners eram registrados ao importar o módulo e o feedback exigia sessão de telemetria.

Agora, a tela inicial apresenta o projeto, a pesquisa e duas escolhas de destaque equivalente. Ambas liberam o transporte imediatamente. A recusa não cria sessão de pesquisa, não inicia rrweb e não instala listeners ou intervalos de captura. Instrumentação chamada pelas funções de transporte permanece inerte sem sessão. O contato informado é `25202874@aluno.univesp.br` (configurável por `PAP_RESEARCH_CONTACT`).

A aceitação explícita registra a versão `research-v6-voluntary` e a data da decisão. Só então inicia a sessão; após o primeiro envio bem-sucedido, inicia rrweb com os parâmetros existentes (canvas a 5 fps, movimentos a cada 50 ms e rolagem a cada 100 ms). O indicador informa gravação ativa. Senhas, formulários de feedback e configurações de pesquisa ficam excluídos da captura visual e dos listeners genéricos pelo marcador `data-private`.

Em falha de inicialização, rede ou resposta HTTP de erro, a pesquisa para e um aviso discreto mantém o transporte disponível. Não há reenvio automático depois de 429/503: isso evita insistência após a falha. É possível tentar novamente nas configurações. Os eventos não enviados são descartados, portanto podem existir lacunas no replay; não se promete captura completa quando a rede falha.

## Persistência e revogação

- `localStorage['pap.research.choice']`: `{state: accepted|declined, version, decidedAt}`. Ausência, versão antiga, objeto inválido ou erro de leitura apresentam novamente as duas escolhas, sem iniciar pesquisa.
- `sessionStorage['pap-usability-*']`: token, identificador e sequência da gravação, separados da decisão. Não são critérios de consentimento.
- `localStorage['pap.research.receipts']`: até 50 comprovantes assinados de sessões, para anexar a um pedido de exclusão. Não autorizam leitura de dados. Se o armazenamento estiver indisponível, os comprovantes ficam só na memória da página.
- Sem prazo de validade artificial. Atualizar `NOTICE_VERSION` em mudanças relevantes de finalidade, dados, acesso ou retenção. Uma aba já aberta com código antigo precisa receber/recarregar a versão nova; não existe atualização remota forçada do aviso.
- O botão de configurações no cabeçalho abre **Participação na pesquisa**. Telas legadas têm um acesso próprio ao mesmo diálogo. Permite consultar decisão, ativar, interromper, ler os detalhes e solicitar exclusão.
- Revogar para rrweb imediatamente, remove listeners e timer, aborta requisições em andamento, limpa fila e credenciais da sessão. Guardas de geração impedem respostas tardias de reativar a captura. Recarregar após a recusa não reinicia a gravação.
- Eventos `storage` sincronizam abas da mesma origem; `BroadcastChannel` também propaga a interrupção. Outras origens, navegadores e aparelhos têm decisões independentes. Trocar o domínio temporário do túnel gera uma nova origem e uma nova escolha.
- Se não for possível persistir, a escolha explícita vale só na página atual; a tela avisa e pergunta novamente na recarga. Nenhuma falha equivale a aceite.

## Feedback e solicitações

O envio voluntário funciona em `/api/research/feedback/`, sem criar sessão. Apenas quando a pesquisa está ativa o cliente envia o token para vincular o relato a uma sessão já existente. A gravação não é pré-requisito para responder ao formulário.

Os novos relatos e pedidos ficam em `~/.local/state/pap/research/messages.sqlite3`, separado do banco de aplicação e de telemetria, com diretório/arquivo privados na criação. A configuração Django `PAP_RESEARCH_DB` permite isolamento em testes. O painel `/admin/research/` exige autenticação administrativa e não é publicado pelo conjunto de URLs do túnel. Ele lista até 200 mensagens recentes, com confirmação para análise ou exclusão da mensagem. Existem limites globais de 30 mensagens/minuto e 10.000 mensagens (configurações Django `PAP_RESEARCH_MESSAGES_PER_MINUTE` e `PAP_RESEARCH_MAX_MESSAGES`).

Uma solicitação gera protocolo e **não executa a exclusão dos registros de navegação**. A equipe deve localizar as sessões pelos comprovantes disponíveis ou pelas informações fornecidas, verificar o pedido e tratar cada armazenamento. Marcar o protocolo como analisado não apaga dados. Não há prazo de resposta aprovado nesta implementação.

### Procedimento de retenção e exclusão

| Categoria | Comportamento atual | Tratamento pendente da equipe |
| --- | --- | --- |
| Eventos de telemetria | Limpeza de eventos com mais de 30 dias durante novo recebimento válido | Sem agendamento independente; conferir expiração se não houver novos envios |
| Blocos comprimidos | Removidos quando a sessão não tem mais eventos | Blocos de sessão parcialmente expirada podem permanecer |
| Cache de JSON/WebM | Exclusão administrativa da sessão remove o diretório de exportações | Sem limpeza automática por idade; verificar tarefas de exportação em andamento |
| Novos relatos e solicitações | Banco separado; exclusão manual de mensagem com confirmação | Sem limpeza automática por prazo; apagar mensagens associadas separadamente quando aplicável |
| Cópias baixadas/backups | Fora da limpeza automática da aplicação | Responsáveis devem localizar e eliminar as cópias abrangidas pelo pedido |
| SQLite | DELETE lógico permite reutilização de páginas | Não garante redução do arquivo nem eliminação física dos bytes |

Nenhum dado real foi apagado, migrado ou compactado nesta tarefa. Não foi instalado agendamento ou serviço. O aviso informa as limitações acima e não garante eliminação de todas as cópias em 30 dias. Não há mudança automática da política para prometer prazo ainda não implementado.

## Verificação

Os testes usam banco principal, telemetria e mensagens em diretórios temporários. Rotas SPTrans e mapas são simulados nos testes de navegador; não há consultas a passageiros reais nem medição da disponibilidade da SPTrans.

Comandos (ambiente Python `~/.virtualenvs/bus`):

```sh
~/.virtualenvs/bus/bin/python backend/manage.py test transit.test_research transit.test_usability transit.test_usability_admin --noinput
npm test --prefix frontend
cd frontend
PATH="$HOME/.virtualenvs/bus/bin:$PATH" npm run test:e2e -- e2e/research-consent.spec.js e2e/selection-flow.spec.js --reporter=line
```

A matriz de testes e as evidências desta revisão estão em `evidencias/consentimento-2026-10-23/`. O build usado pelo teste E2E compila o React em `frontend/dist`. O aviso de bundle acima de 500 kB continua presente; custo de CPU/memória e rede em aparelhos físicos ainda não foi medido. A importação da biblioteca rrweb continua no bundle, mas sua captura só é iniciada depois do aceite.

## Operação e limites restantes

- Recarregar o frontend compilado para ver o novo aviso. Um Gunicorn já iniciado precisa recarregar/reiniciar sua instância para reconhecer as novas APIs; não houve reinício de servidores de desenvolvimento ou túneis nesta tarefa.
- O consentimento controla a captura da aplicação. Logs operacionais do servidor e consultas aos provedores de transporte/geocodificação continuam existindo.
- Revogação não desfaz um envio já recebido pelo servidor. Interrupção é imediata no cliente; remoção retroativa depende do pedido e do procedimento administrativo.
- Comprovantes deste navegador não localizam automaticamente sessões antigas, de outros domínios ou de aparelhos diferentes.
- Feedback novo é independente do exportador de eventos antigo: aparece no painel de mensagens e, quando vinculado, no detalhe do replay pelo horário de recebimento. Não é inserido retroativamente no JSON exportado da telemetria.
- O painel administrativo mostra as 200 mensagens mais recentes; uma busca/paginação é evolução posterior se o volume justificar.
- As métricas de rota, a coleta de avaliações externas e o relatório acadêmico não foram alterados.

As orientações para uma futura atualização acadêmica estão em [ATUALIZACAO_RELATORIO_CONSENTIMENTO.md](ATUALIZACAO_RELATORIO_CONSENTIMENTO.md); nenhuma edição foi aplicada ao worktree `relatorio`.
