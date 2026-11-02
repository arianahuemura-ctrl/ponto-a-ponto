# Estado do projeto para continuidade

Atualizado em **02/11/2026**, referência de data `America/Sao_Paulo`.
Este é um resumo verificado do repositório, não uma recuperação da conversa.
Na próxima sessão, leia [AGENTS.md](../AGENTS.md) e confira o Git novamente.
Procedimento e diagnóstico: [CODEX_CONTINUITY.md](CODEX_CONTINUITY.md).

## Versionamento autorizado em 02/11/2026

- Código do aplicativo consolidado no commit `80a35640eaf537a7df72ef77aebaa62b0d8159bb`.
- O responsável autorizou commits e pushes das branches `feat/busca-bidirecional`
  e `relatorio`. Referências anteriores: `34a46f29` e `e5077b9`; consultar o Git
  para os commits desta publicação. Os registros históricos de “sem commit”
  abaixo descrevem o momento das respectivas etapas, anterior à autorização.
- Frontend: `npm --prefix frontend test`, **15/15 aprovados**; build aprovado.
  Playwright dos arquivos `rail-network`, `rail-routing`, `async-routes`,
  `feedback-rating` e `point-controls`: **12/12 aprovados**, servidor de teste local.
- Backend: `.venv/bin/python backend/manage.py test transit --noinput`,
  **501 testes, 2 falhas e 1 erro**. Permanecem os três casos de concorrência
  já registrados: `test_progressive_yields_before_pedestrian_requests_and_can_close`,
  `test_verified_walk_streams_before_bus_preparation_and_can_close` e
  `test_early_walk_preserves_later_faster_bus_and_final_status`.
  Não confundir este commit de desenvolvimento com aprovação integral da suíte.
- A tentativa conjunta `test transit mbm` usou configuração inadequada para os
  contratos públicos e sofreu bloqueios do sandbox. A execução pública separada
  ficou impedida por ausência de `whitenoise` neste virtualenv; as dependências
  adicionais já constam em `requirements-public.txt`. Nenhuma dependência global
  foi instalada. Logs completos: `.cache/setup/commits-push-20261102/`.
- O fetch normal encontrou uma referência interna inválida em `refs/codex/`.
  A consulta ao remoto foi feita por um repositório temporário isolado, sem apagar
  referências ou alterar histórico. Remoto sem divergência nas duas branches.
- Código, testes, documentação e evidências selecionadas compõem a publicação nas
  branches próprias. Bancos, caches, configurações privadas e mídias externas
  permanecem locais. Relatório: PDF editorial validado de 167 páginas.

## Estado atual e referência Git

- Projeto **Ponto a Ponto (PaP)**, protótipo acadêmico UNIVESP de consulta e
  planejamento de transporte, iniciado em Mauá e integrado ao GTFS de São Paulo.
- Branch inspecionada: `feat/busca-bidirecional`.
- HEAD: `34a46f29c2b541af495a0b7c86eb565071b37116`, de 28/10/2026,
  `feat: salva locais favoritos e adiciona atalhos Casa e Trabalho`.
- Antes desta documentação: **56 arquivos rastreados modificados e 157 não
  rastreados**, contados com `git status --porcelain=v1 -uall`. Sem alterações
  no índice. Essa contagem não inclui arquivos ignorados nem os três novos
  documentos de continuidade. Não é uma árvore limpa.
- Os commits anteriores incluem recuperação de carregamento (`01da6e6`),
  feedback público e alternativas progressivas (`99655dd`), itinerários e
  pesquisa (`85417bc`) e isolamento público com Gunicorn/Cloudflare (`aee66eb`).
- A árvore de trabalho contém desenvolvimento posterior ao HEAD: multimodalidade,
  custos ponderados, materializações, publicação concorrente, ARTESP e ajustes
  de interface. Há código, testes, relatórios e experimentos ainda sem commit.
  A intenção de tarefas anteriores não foi reconstruída a partir das sessões.

## Arquitetura e principais componentes

| Área | Componentes e responsabilidade |
| --- | --- |
| Aplicação web | Django/Python: `backend/mbm/settings.py`, `urls.py`, `backend/transit/`; configuração carregada pelo módulo `environment.py`. |
| Interface | React/Vite/Leaflet em `frontend/src/`; `SaoPaulo.jsx`, `SaoPauloMap.jsx`, `BoardDialog.jsx`, `DestinationSearch.jsx`, `StopCanvas.js` e hooks de previsões. Scripts e dependências em `frontend/package.json` (Node >=24). |
| Dados da aplicação | `db.sqlite3`: administração, catálogo e demonstração; modelos/migrações em `backend/transit/`. A demonstração usa dados simulados. |
| Transporte GTFS | `backend/transit/sptrans/store.py`; catálogo selecionado por `SPTRANS_DATABASE`, separado do banco Django. `SPTRANS_LEGACY_DATABASE` permite fonte suplementar com contexto isolado por trabalhador. |
| Planejamento | `planner.py`, `weighted_planner.py`, `alternatives.py`, `journey_completion.py`, `transfer_policy.py`; leitores de materializações, índice antigo, busca por rodadas e caminhada. |
| Materializações | `materialized_connections.py`, `staged_materialized.py`, `expanded_materialized.py`, `topup_materialized.py`, `short_walks.py`, kernels C++ e comandos de gestão. Bancos derivados separados, assinaturas e checkpoints. |
| Fontes externas | `client.py`/`realtime.py` (Olho Vivo), `addresses.py` (Photon), `walking.py`/`walk_artifacts.py` (percursos pedestres); `merged_gtfs.py` e `import_artesp` para base combinada. |
| Pesquisa/usabilidade | `research.py`, `usability.py`, telas administrativas, `Feedback.jsx`, `researchApi.js`, rrweb e scripts de exportação de replay. |
| Execução pública | `start_server.py`, `backend/mbm/public_settings.py`, `public_urls.py`, `public_boundary.py`, `scripts/public_instance.py`, scripts Gunicorn/túnel. Rotas administrativas excluídas da configuração pública. |
| Verificação | Testes Django em `backend/transit/test_*.py` e `backend/mbm/test_public.py`; unitários JS e Playwright em `frontend/`; evidências em `docs/verificacoes/` e `artifacts/benchmarks/`. |

## Funcionalidades presentes

Conferidas no código e documentação local; presença não implica validação integral
ou implantação atual de cada funcionalidade.

- Seleção de embarque/destino no mapa, QR Code, busca de endereços, itinerários,
  previsões, acompanhamento de ônibus, favoritos e atalhos Casa/Trabalho.
  Origem/destino usam `sessionStorage`; favoritos persistem em `localStorage`.
- Catálogo GTFS e distinção entre programação, estimativa e previsão ao vivo;
  API Olho Vivo depende de credencial e correspondência válida de linha/parada.
- Pesquisa, feedback público, registro de usabilidade e replay administrativo.
  A árvore local acrescenta nota opcional de 1 a 5 e ajustes de controles;
  veja [feedback-rating.md](feedback-rating.md) e `research.py`/`Feedback.jsx`.
- Ônibus, metrô e trem com cores/identificação ferroviárias, conexões internas
  e custos ponderados. Implementações locais em `rail.py`, `rail_network.py`,
  `transfer_policy.py` e componentes correspondentes no frontend.
- Alternativas progressivas SSE/NDJSON. `_multimodal_progressive` em
  `alternatives.py` usa `concurrent_sources.merge` para fontes preparadas,
  índice de ônibus, busca multimodal, caminhada e fonte legada configurável.
- Importação ARTESP e materialização combinada presentes na árvore local.
  Os [registros de ativação](../artifacts/benchmarks/artesp-activation-20261102.json)
  informam ativação em 02/11 e catálogo HTTP com 47.379 pontos, 25.105 ARTESP.
  Isso é evidência daquela execução; essa contagem não foi revalidada na retomada
  pública descrita abaixo.
  A [auditoria de Mauá](maua-artesp-audit-20261102.md) registra 337 pontos ARTESP,
  16 linhas/variantes e 705 viagens programadas para 03/11/2026, sem afirmar
  cobertura integral municipal ou operação observada.

## Decisões técnicas a preservar

- Separar demonstração, GTFS e artefatos derivados. Não substituir bancos nem
  regenerar materializações como efeito colateral de retomada. Assinaturas
  invalidam artefatos incompatíveis; checkpoints não equivalem a geração completa.
- Primeiro embarque custa zero; troca envolvendo ônibus ou caminhada externa
  custa 1; transferência ferroviária interna custa 1/3, representada em inteiros
  em terços. Seleção de até cinco rotas de transporte prioriza menor custo e
  respeita `min(max_transfers, mínimo encontrado + 1)`. Ver
  [weighted-transfers.md](weighted-transfers.md) e `transfer_policy.py`.
- Não confundir custo de transferência com quantidade física de trocas, nem
  cobertura estrutural de pares com serviço disponível em um horário.
- Caminhadas externas exigem percurso verificado; linha reta não substitui
  geometria pedestre. Integrações internas ferroviárias são explícitas e seus
  tempos são estimativas. Não inventar posição de trem nem previsão ARTESP.
- A fonte ARTESP usa identificadores `artesp:`; `realtime.py` rejeita esses
  identificadores antes de consultar previsões/posições SPTrans.
- Cada fonte concorrente abre sua conexão SQLite na própria thread. Publicação
  parcial preserva rotas verificadas; saturação, falha e limite de busca devem
  continuar explícitos. Ver [async-route-stream.md](async-route-stream.md).
- O gerador legado de ônibus com um/dois embarques não define todo o planejador
  multimodal atual. `staged_adapter.py` consulta as novas materializações e
  `supplementary.py` preserva o uso da base anterior quando configurada.
- Geração combinada usa processos isolados e escrita coordenada, etapas e
  reserva de disco. Não iniciar expansão exaustiva por supor capacidade livre.
  Ver [staged-materialization.md](staged-materialization.md) e
  [artesp-materialization.md](artesp-materialization.md).

## Trabalho em andamento e pendências

- Consolidar/revisar o grande conjunto de mudanças locais. Não há evidência de
  que todo esse conjunto esteja integrado, validado e pronto para commit.
- O registro da ativação ARTESP informa **três falhas preexistentes de testes de
  concorrência** numa execução mais ampla. O resumo JSON não identifica os três
  testes; reproduzir e identificar antes de corrigir ou declarar suíte verde.
- Reconciliar a abertura do README sobre o planejador de dois ônibus com o fluxo
  multimodal local e a cronologia dos relatórios. Documentos de capacidade e
  cobertura descrevem bases de momentos diferentes, não o mesmo estado atual.
- A comparação assíncrona registra melhora de cauda, mas aumento da mediana sob
  carga (0,282 → 0,599 s nos 1.637 casos com sucesso nos dois fluxos). Investigar
  priorização da materialização frente às buscas pesadas; não prometer ganho
  uniforme. Ver [async-performance-comparison.md](async-performance-comparison.md).
- A [auditoria de cobertura](coverage-audit-20261101.md) identifica limites de
  acesso e encaixe pedestre, buscas inconclusivas e dependência externa. Seus
  99,6659% de pares materializados referem-se à base anterior, não a Mauá nem
  à base combinada. Falta comprovar latência ponta a ponta no celular.
- ARTESP: horários intermediários interpolados, calendário de 2026 sem exceções
  de feriados; rede municipal Suzantur não está integralmente incluída. Revisar
  vigência antes de extrapolar disponibilidade para outras datas.
- Avaliação presencial com passageiros e implantação física de QR Codes não são
  demonstradas pelos testes e auditorias consultados; continuam pendências.

## Últimos testes e resultados conhecidos

| Data / origem | Escopo e resultado | Evidência e limites |
| --- | --- | --- |
| 02/11/2026, esta sessão | `npm --prefix frontend test`: **14 aprovados**, 0 falhas, 0 ignorados, saída 0. | Log local completo: `.cache/setup/codex-continuity-20261102-wu2c941p/javascript.log`; metadados em `summary.json` na mesma pasta. Não inclui Playwright ou backend. |
| 02/11/2026, registro anterior | **60 testes específicos aprovados**, **3 falhas preexistentes** na execução mais ampla. | [artesp-activation-20261102.json](../artifacts/benchmarks/artesp-activation-20261102.json), campos `focused_tests_passed` e `preexisting_concurrency_test_failures`; contexto em [artesp-materialization.md](artesp-materialization.md). Não reexecutados aqui. |
| 02/11/2026, registro anterior | **42 testes aprovados** de importação, geração paralela e caminhadas; integridade SQLite `ok` e equivalência amostral sequencial/paralela. | [artesp-materialization-20261102.json](../artifacts/benchmarks/artesp-materialization-20261102.json), `tests` e `validation_before_walking_reservations`. Não reexecutados aqui. |
| 01/11/2026, documento anterior | **127 testes backend e 3 de navegador aprovados**, segundo o documento. | [async-route-stream.md](async-route-stream.md). A contagem é relato documental; o JSON de primeira rota é uma medição funcional, não log dessa suíte. |

Na etapa inicial de documentação não foram executados Django, Playwright, build,
testes de carga, importações ou novas consultas ao servidor público. Não há
resultado atual da suíte completa. Logs sob `.cache/setup/` são locais e
ignorados pelo Git: não estarão automaticamente disponíveis em outro clone.

Validação documental desta sessão: links locais, cercas de código e espaços
finais conferidos sem erros. HEAD e hash do diff rastreado permaneceram iguais;
tamanho e data de modificação dos 576 arquivos preexistentes inventariados foram
preservados. Somente os três documentos de continuidade foram acrescentados fora
dos caminhos ignorados. Registro local: `.cache/setup/codex-continuity-20261102-wu2c941p/documentation-check.json`.

## Execução pública retomada em 02/11/2026

- A pedido do responsável, o PaP foi colocado novamente no ar. O processo público
  estava inativo e o contêiner `pap-tunnel` estava parado (saída 255, sem indicação
  de OOM; a causa não foi determinada).
- O túnel anterior usava `clone-thickness-sacramento-certainly.trycloudflare.com`.
  O reinício do Quick Tunnel gerou outro endereço temporário:
  **https://fantastic-plants-sufficient-visitor.trycloudflare.com**.
  Não presumir que esse endereço sobreviverá a outro reinício do túnel.
- Comandos executados: `docker start pap-tunnel` e `bash scripts/start_public.sh`.
  O script detectou o domínio e iniciou Gunicorn em `127.0.0.1:8001`, com
  `DEBUG=False`; o check Django terminou sem problemas. Foram reutilizados o
  build existente e a configuração atual de bancos, sem importação ou reconstrução.
- Verificação HTTPS: saúde, `/?stop=5614798`, `/?stop=440016922`,
  `/?location=-23.561326733117216,%20-46.65615056649423` e o bundle JavaScript
  retornaram HTTP 200. Não foram testadas interações no navegador, previsões ou
  a linha problemática mencionada pelo responsável.
- Evidência local: `.cache/setup/pap-public-restart-20261102-m3xbhao8/http-check.json`.
  Log do processo: `~/.cache/pap-public/880e7c7501f4/gunicorn.log`.
  Para uma nova retomada, verificar o túnel existente antes de reiniciá-lo;
  o script de início reaproveita a instância ativa quando o domínio coincide.

## Próximas tarefas recomendadas

1. Conferir a árvore atual e revisar mudanças por área, preservando todos os
   arquivos locais. Preparar unidades de revisão/commit pelo fluxo normal.
2. Reproduzir as três falhas de concorrência, guardar logs completos e registrar
   nomes/causas. Depois executar as suítes pertinentes ao conjunto revisado.
3. Atualizar README e referências que misturam escopos antigos e atuais.
4. Investigar latência e regras de acesso com os experimentos já existentes em
   `scripts/experiments/`; distinguir medição local de ponta a ponta.
5. Planejar revisão de calendário/cobertura ARTESP e avaliação com passageiros.

Comandos de referência, após conferir ambiente e escopo: `.venv/bin/python
backend/manage.py test transit mbm`, `npm --prefix frontend test` e, com o
ambiente Python ativo, `npm --prefix frontend run test:e2e`. Playwright compila
a interface e inicia servidor de teste em 18081, conforme sua configuração.
Capture saídas conforme o [procedimento de continuidade](CODEX_CONTINUITY.md).

## Vídeo de apresentação — revisão de tempos em 02/11/2026

- Fonte confirmada pelo responsável: `/home/avale/Documentos/univesp/PI2/entrega-2026-11-02-enquadramento-ariana/PaP_integral_gravacoes_PT_EN.mp4`.
- Nova entrega: `/home/avale/Documentos/univesp/PI2/entrega-2026-11-02-tempos-revisados/PaP_integral_gravacoes_PT_EN.mp4`.
  O original foi preservado, com SHA-256 conferido antes e depois.
- Removido o resíduo vocal “quatro” após “custos zero e um”, em 05:14,800 do
  original. Restaurada a fala ferroviária de 04:44,433–04:53,300 a partir de
  `rail.wav` já existente: `rail-normal.wav` arquivado continha apenas o início
  da fala, deixando silêncio prolongado. Não houve nova síntese de voz.
- Avisos, favoritos, lista de alternativas e painel de pesquisa ajustados aos
  assuntos da narração; o painel completo de pesquisa passou de cerca de 38,7 s
  para 11,5 s, seguido por imagens específicas. Enquadramentos existentes mantidos.
- Retirados 5,5 s de pausas silenciosas, incluindo a sobra do encerramento:
  duração final **09:43,367**, 17.501 quadros a 30 fps, 1920 × 1080.
- Validação: decodificação integral sem erros; 169 legendas PT e 165 EN, textos
  preservados, SRT/VTT conferidos com as faixas internas; 12 capítulos retimados;
  12 amostras visuais fora das alterações e 13 corrigidas conferidas na exportação.
- A pasta da entrega contém `Revisao_tempos.md`, `validacao.json`, comparativos e
  hashes. Scripts, análises locais de áudio e registros completos estão em
  `/home/avale/Documentos/univesp/PI2/producao_video/2026-11-02-tempos-revisados/`.
  Essa entrega foi posteriormente usada como fonte da revisão de rótulos abaixo.
  Esses materiais estão fora do Git deste repositório. A revisão usou transcrição
  integral local, medições de áudio, cronologia das cenas e amostras visuais;
  transcrições automáticas não devem substituir as legendas revisadas.

## Nomes ferroviários e camadas do mapa — 02/11/2026

- Solicitação confirmada: corrigir **aplicativo e vídeo**, usando o mesmo padrão
  para todos os nomes ferroviários. Referência Git permanece em
  `feat/busca-bidirecional`, HEAD `34a46f2`; alterações locais sem commit.
- `railStyle.js` centraliza os nomes: **Metrô Linha Amarela**, **Metrô Linha
  Verde**, **CPTM Linha 12 Safira**, etc. Mapa, legendas, alternativas, detalhes
  de conexão, seletores e nomes acessíveis compartilham a função. Os identificadores
  GTFS e as cores existentes foram preservados. Códigos desconhecidos continuam
  identificados pelo dado recebido, sem inventar uma cor ou nome de linha.
- `railLabelLayout.js` posiciona caixas fora dos trilhos, dos marcadores e dos
  controles, com linhas de ligação; recalcula após movimento/zoom e mudança dos
  pontos. Textos podem quebrar em duas linhas em telas estreitas. Se não houver
  espaço livre, omite o rótulo naquele enquadramento em vez de cobrir um ponto.
- O canvas de pontos passou a um pane Leaflet próprio (`450`), mantendo o
  alinhamento durante movimento e zoom. Rótulos (`410`) ficam abaixo dos pontos;
  o passageiro tem pane próprio (`750`), acima das outras camadas do mapa.
  O canvas avisa quando novos pontos já foram projetados para atualizar obstáculos.
- Validação final: **63 testes JS aprovados**, via `npm --prefix frontend test`;
  **11 testes Playwright aprovados**, em `rail-network.spec.js`,
  `rail-colors.spec.js` e `rail-routing.spec.js`. Cobrem nomes, cores nos dois
  temas, telas estreitas/amplas, conexões, zoom, deslocamento, alinhamento do
  canvas e passageiro acima de um ponto coincidente. Build Vite concluído.
  Logs: `.cache/setup/rail-labels-20261102-w4yiv6q0/unit-verified.log` e
  `e2e-verified.log`. `git diff --check` sem erros.
- A verificação ampliada identificou testes legados incompatíveis com a interface
  atual: dois de `boarding-markers.spec.js` e quatro de `location-query.spec.js`
  inicialmente pararam no consentimento. Uma preparação temporária permitiu
  avançar, mas quatro continuaram falhando por procurar marcadores DOM ou o botão
  removido `Alterar embarque`. Esses ajustes temporários não foram mantidos.
  A suíte completa não foi declarada aprovada; atualizar esses cenários é pendência.
  Evidências: `e2e-host.log` e `e2e-host-v2.log`, na mesma pasta de logs.
- Gunicorn público recarregado após o build, validando identidade e instante de
  início do processo. Túnel preservado. Na URL pública já registrada acima:
  saúde e os dois links de parada retornaram HTTP 200; o navegador abriu o
  cenário simulado do MASP, exibiu nomes novos e confirmou o passageiro no topo,
  sem erros JavaScript. Evidência arquivada com a produção do vídeo:
  `public-check.json`, `public-final.png` e `public-smoke.log`.
- **Atenção ao próximo build:** Playwright recompila `frontend/dist`; o servidor
  público usa WhiteNoise sem atualização automática. Depois de publicar outro
  build, recarregar o processo público validado para registrar os novos assets.
  Não reiniciar o túnel apenas para atualizar a interface.

## Vídeo — rótulos ferroviários em 02/11/2026

- Entrega desta revisão: `/home/avale/Documentos/univesp/PI2/entrega-2026-11-02-rotulos-ferroviarios/PaP_integral_gravacoes_PT_EN.mp4`.
- Fonte: versão `entrega-2026-11-02-tempos-revisados`, preservada com SHA-256
  conferido. Novas capturas reais do aplicativo substituem as cenas pertinentes;
  retratos usam as fontes originais e a calibração de enquadramento aprovada.
  Não houve nova síntese de voz. A conclusão também identifica a CPTM Linha 10
  Turquesa pelo padrão solicitado.
- Mantidos **09:43,367**, 17.501 quadros, 30 fps, 1920 × 1080. Limites dos
  popups e correções de áudio da revisão anterior preservados. Áudio e duas
  faixas internas de legendas copiados sem recodificação: hashes dos dados
  codificados idênticos aos da fonte. SRT/VTT e os 12 capítulos também idênticos.
- Decodificação integral sem erros; nove amostras modificadas e nove preservadas
  comparadas na exportação. A pasta contém `Revisao_rotulos.md`, `validacao.json`,
  `Comparacao_rotulos.jpg` e hashes dos arquivos; cópias publicadas conferidas.
- Scripts, capturas, registros e uma cópia dos arquivos relevantes da interface:
  `/home/avale/Documentos/univesp/PI2/producao_video/2026-11-02-rotulos-ferroviarios/`.
  As entregas anteriores, histórico Git, bancos, configurações globais e sessões
  do Codex foram preservados.

## Vídeo — enquadramento do André em 02/11/2026

- Entrega desta revisão: `/home/avale/Documentos/univesp/PI2/entrega-2026-11-02-enquadramento-andre/PaP_integral_gravacoes_PT_EN.mp4`.
  Derivada da revisão de rótulos, que permanece preservada com SHA-256 conferido.
- Correção solicitada após imagem do corte no cabelo: o recorte de 360 × 270
  aplicado ao `human-0.mkv` cortava o topo da cabeça quando André erguia a
  cabeça. A fonte original contém o cabelo completo.
- Ampliada a área de composição **33 pixels para cima**, para 360 × 303,
  mantendo escala, proporções e posição dos olhos. Fundo recomposto com as
  mesmas capturas da revisão anterior; nenhuma alteração no aplicativo.
- Corrigidos somente os **710 quadros iniciais (00:00–00:23,667)**. Verificação
  da máscara em todos esses quadros encontrou margem mínima de **11 pixels**
  acima do cabelo. Dez amostras da exportação comparadas com a composição.
- Os **16.791 quadros restantes** foram copiados a partir do keyframe 710,
  sem recodificação. Hash do vídeo decodificado desse trecho é idêntico ao da
  fonte. Decodificação completa passou; tempos de todos os quadros, áudio,
  legendas internas, SRT/VTT e 12 capítulos preservados. Duração continua
  **09:43,367**, 17.501 quadros, 1920 × 1080 a 30 fps.
- Entrega inclui `Revisao_enquadramento.md`, `Comparacao_enquadramento.jpg`,
  `validacao.json` e hashes. Scripts, medições e capturas arquivados em
  `/home/avale/Documentos/univesp/PI2/producao_video/2026-11-02-enquadramento-andre/`.
  Cópias publicadas conferidas por hash. As versões anteriores foram preservadas.

## Vídeo — fundamentação revisada em 02/11/2026

- Entrega desta revisão: `/home/avale/Documentos/univesp/PI2/entrega-2026-11-02-fundamentacao-revisada/PaP_integral_gravacoes_PT_EN.mp4`.
  Derivada de `entrega-2026-11-02-enquadramento-andre`, preservada por hash.
- Solicitação: trecho rápido e vestígios da interface antiga perto de **01:14**.
  Confirmado um flash da antiga tela de favoritos sob o cartão “Estruturas de
  Dados”, antes da captura atual. A revisão anterior não havia substituído esse
  intervalo final da fundamentação.
- Recompostos os **879 quadros de 00:49,600 a 01:18,900**, usando fundos inteiros
  limpos e a gravação original da Ariana com a calibração existente. Três telas
  entram completas e permanecem estáveis: fundamentação/IHC por **8,1 s**,
  Nielsen e Norman por **10 s**, RAPTOR/Estruturas de Dados por **11,2 s**.
  A última aproveita o trecho que antes mostrava brevemente favoritos; o mapa
  retorna em 01:18,900. Fala original preservada, sem corte ou mudança de velocidade.
- Verificados os fundos de **todos os 879 quadros**, incluindo bordas, contra
  as imagens limpas. Quinze amostras de composição e as transições de entrada/
  saída foram conferidas na exportação. Decodificação integral aprovada.
- Os **16.622 quadros fora da alteração** são idênticos após decodificação,
  incluindo a abertura corrigida do André. Áudio, legendas internas, SRT/VTT,
  12 capítulos e tempos dos quatro fluxos de vídeo/áudio/legendas permanecem
  iguais. Duração: **09:43,367**, 17.501 quadros, 1920 × 1080, 30 fps.
- Entrega inclui `Revisao_fundamentacao.md`, `Comparacao_fundamentacao.jpg`,
  `validacao.json` e hashes. Scripts, medições de todos os fundos e capturas:
  `/home/avale/Documentos/univesp/PI2/producao_video/2026-11-02-fundamentacao-revisada/`.
  Cópias publicadas verificadas. Nenhuma alteração no aplicativo ou nas versões
  anteriores; somente o estado de continuidade foi atualizado no repositório.

## Vídeo — lâmpada e dimmer em 02/11/2026

- Entrega desta revisão: `/home/avale/Documentos/univesp/PI2/entrega-2026-11-02-lampada-dimmer/PaP_integral_gravacoes_PT_EN.mp4`.
  A mesma pasta contém `Trecho_lampada_dimmer.mp4`, com **22,733 s**, para revisão
  direta da cena, além de imagem comparativa, notas, validação e hashes.
- Fonte preservada: versão `2026-11-02-fundamentacao-revisada`. Substituída a
  imagem parada por captura real do aplicativo entre **01:27,233 e 01:49,967**:
  zoom out em quatro passos, lâmpada apagada/acesa, pressão e arraste do dimmer,
  seguidos do retorno à localização do passageiro na narração correspondente.
- Estados conferidos no navegador: lâmpada apagada com opacidade **0,25**;
  acesa com **1**; dimmer percorrendo transparência **0 → 100 → 60%**, finalizando
  em opacidade **0,4**. Localização emulada no MASP; pesquisa recusada. Somente
  o ponteiro visível foi acrescentado à captura; código do aplicativo preservado.
- Enquadramento conferido contra os **180 pontos** do mapa do minianel vinculado
  pela [Prefeitura](https://prefeitura.sp.gov.br/w/servico/rodizio). Limites da
  referência: norte −23,50685, sul −23,63102, oeste −46,75073, leste −46,57048.
  A vista capturada em zoom 12 inclui tudo, com a borda sul visível acima da
  barra inferior (limite sul desobstruído −23,63855). Foi necessário pequeno
  deslocamento após o zoom para evitar que a barra encobrisse essa extremidade.
- Montagem sincronizada com áudio original: esperas de carregamento retiradas
  e passos de zoom exibidos com quadros estabilizados. Não tratar o tempo da
  montagem como medição de desempenho. A gravação ampla mostrou esperas com
  cerca de **20 mil pontos**; investigar separadamente sem a instrumentação
  de captura antes de atribuir causa ou prometer desempenho.
- Validação: **682 quadros** da demonstração comparados com a captura; estados
  e enquadramento conferidos; decodificação integral aprovada. Os **16.751
  quadros fora do bloco reencodificado** são idênticos após decodificação,
  incluindo as correções da abertura do André e da fundamentação. Os 68 quadros
  seguintes da busca foram reencodificados até o próximo keyframe, em 01:52,233,
  mantendo o conteúdo original, com amostras verificadas.
- Áudio, duas faixas de legendas, SRT/VTT, 12 capítulos e tempos dos fluxos
  preservados. Vídeo completo continua com **09:43,367**, 17.501 quadros,
  1920 × 1080 a 30 fps. Hashes dos arquivos publicados conferidos.
- Produção: `/home/avale/Documentos/univesp/PI2/producao_video/2026-11-02-lampada-dimmer/`.
  Inclui `capture-completa.mp4`, `take3/capture.json`, mapa KML, `timeline-v2.json`,
  `app-demo-v2.mkv` sem perdas, `replay.py`, `validate.py` e `Reproducao.md`.
  A reprodução usa o clipe sem perdas; não depende dos milhares de JPEGs temporários.

## Rótulos únicos por linha — 02/11/2026

- Removida a segunda rodada de posicionamento em `frontend/src/railLabelLayout.js`.
  Cada nome aparece no máximo uma vez na área visível, inclusive quando a fonte
  divide a linha em vários trechos. Mantidas as restrições contra sobreposição
  com trilhos, marcadores e controles; o passageiro continua acima das camadas.
- Regressão unitária cobre linha longa, geometrias múltiplas, entrada duplicada
  e linha distinta. Teste de navegador verifica unicidade após zoom e deslocamento,
  em telas estreita e larga. `npm --prefix frontend test`: **64 aprovados**;
  `PATH="$PWD/.venv/bin:$PATH" npm --prefix frontend run test:e2e -- e2e/rail-network.spec.js`:
  **4 aprovados**, incluindo build. Logs em `.cache/setup/unique-rail-labels-20261102/`.
- Gunicorn recarregado após o build, mantendo o túnel existente. Verificação em
  `https://fantastic-plants-sufficient-visitor.trycloudflare.com` confirmou saúde
  e links dos pontos com HTTP 200, rótulos únicos, passageiro acima das camadas
  e ausência de erros JavaScript. Alterações locais, ainda sem commit.
- Entrega desta revisão: `/home/avale/Documentos/univesp/PI2/entrega-2026-11-02-rotulos-unicos/PaP_integral_gravacoes_PT_EN.mp4`,
  derivado da entrega `2026-11-02-lampada-dimmer`, preservada por hash. Capturas
  atualizadas em **7.226 quadros**, incluindo mapas amplos e a demonstração
  dinâmica da lâmpada. A primeira consulta Mauá–Brás atingiu o limite de cálculo;
  a segunda retornou a conexão real e foi utilizada, sem interceptar respostas.
- Abertura recomposta com o retrato ampliado para cima, preservando a cabeça do
  André. Fundamentação limpa e pausada mantida. Lâmpada recapturada com o mesmo
  intervalo de 682 quadros, zoom sobre todo o centro expandido e dimmer
  **0 → 100 → 60%**. A primeira tomada apresentou popup durante o arraste;
  a segunda o fecha pela interface antes de mostrar a área ampliada.
- Validação final aprovada: **17.501 quadros**, **09:43,367**, 1920 × 1080,
  30 fps; decodificação integral; áudio e legendas internas idênticos por hash;
  timestamps dos pacotes, 12 capítulos e SRT/VTT preservados. Conferidas 16
  amostras de quadros recompostos, 14 de conteúdo preservado e 11 da demonstração.
  Vídeo reencodificado: não declarar identidade de pixels nas cenas preservadas.
- Entrega inclui `Trecho_lampada_dimmer.mp4`, comparação visual, notas,
  `validacao.json` e hashes. Arquivos publicados conferidos por hash. Produção:
  `/home/avale/Documentos/univesp/PI2/producao_video/2026-11-02-rotulos-unicos/`;
  contém capturas, scripts, logs, `take2/capture.json`, `app-demo.mkv` sem perdas
  e instruções de reprodução. Todas as versões anteriores permanecem disponíveis.

## Vídeo — emenda da voz do Bruno em 02/11/2026

- Entrega: `/home/avale/Documentos/univesp/PI2/entrega-2026-11-02-voz-bruno-revisada/PaP_integral_gravacoes_PT_EN.mp4`.
  Inclui `Trecho_Bruno_02m56s.mp4` (20 s), notas, validação e hashes. Derivada
  de `entrega-2026-11-02-rotulos-unicos`, preservada por hash.
- Relato de voz dupla em 03:03 coincide com a antiga substituição pontual de
  “real” por “total”. Fonte em `2026-10-28-bruno/correcao-palavra/`: recorte
  sintetizado de 1,425–1,810 s avançava sobre a articulação seguinte. Encurtado
  para 1,425–1,690 s, preservando o “das” original. Não houve nova síntese.
- Alterados **0,36 s**, entre **182,897833 e 183,257833 s**, com alinhamento
  por correlação, duração mantida e rampas de 4 ms. RMS igualado à emenda
  anterior; pico medido no AAC da vizinhança: **−2,16 dBTP**. PCM fora da
  emenda idêntico antes da codificação; áudio completo recodificado em AAC
  192 kbps, sem ajuste global de volume.
- Vídeo e duas faixas internas de legendas **idênticos por hash dos fluxos**;
  capítulos, SRT/VTT e duração preservados: **17.501 quadros, 09:43,367**.
  Decodificação integral do áudio aprovada. Transcrição local Whisper large-v3
  da frase exportada confirma “O painel separa o tempo total das caminhadas e
  identifica os pontos de troca”. Conferência por alinhamento, espectrograma,
  níveis e transcrição; não houve escuta humana nesta revisão.
- Produção e evidências: `/home/avale/Documentos/univesp/PI2/producao_video/2026-11-02-voz-bruno-revisada/`.
  Publicação conferida por hash. Aplicativo e testes não alterados nem
  reexecutados nesta etapa; somente documentação de continuidade no repositório.

## Vídeo — animação do rosto da Úrsula em 02/11/2026

- Entrega: `/home/avale/Documentos/univesp/PI2/entrega-2026-11-02-ursula-rosto-natural/PaP_integral_gravacoes_PT_EN.mp4`.
  Inclui comparação animada de **10 s**, ampliada lado a lado, notas, validação
  e hashes. Fonte `2026-11-02-voz-bruno-revisada` preservada integralmente.
- Diagnóstico no gerador antigo: máscara parcial, preenchimento de pele com
  cor fixa e redimensionamento de um recorte da boca deixavam contorno residual;
  pinta e queixo ficavam fora da animação. Novo gerador usa deformação contínua
  do recorte original, sem segunda boca sobreposta. Região da pinta preserva
  o tamanho enquanto se desloca com a mandíbula; olhos, nariz, cabelo e ombro
  permanecem estáveis.
- **61 poses** conferidas: transformação sem dobras; pinta visível em todas,
  deslocando-se aproximadamente **24,54 px** entre extremos no retrato final.
  Movimento ilustrativo guiado pela energia do áudio e suavizado entre quadros;
  não confundir com sincronização fonética por visemas.
- Atualizadas quatro falas da Ingrid/Úrsula e sua apresentação na grade de
  integrantes. **2.702 quadros** modificados dentro de blocos de keyframes que
  somam 3.243 quadros reencodificados. Os **14.258 quadros restantes são
  idênticos após decodificação**. Decodificação integral aprovada e 17 amostras
  da composição exportada verificadas.
- Áudio e duas faixas internas de legendas idênticos por hash dos fluxos:
  correção do Bruno preservada. SRT/VTT, capítulos e timestamps mantidos;
  duração **09:43,367**, 17.501 quadros, 1920 × 1080, 30 fps. Nenhuma nova voz.
- Produção: `/home/avale/Documentos/univesp/PI2/producao_video/2026-11-02-ursula-rosto-natural/`.
  Contém gerador `rig.py`, poses, scripts de montagem/validação, logs e evidências.
  Entrega e fontes publicadas verificadas por hash. Aplicativo inalterado;
  somente documentação de continuidade atualizada no repositório.

## Vídeo — boca e mandíbula do King Bradley em 02/11/2026

- Entrega: `/home/avale/Documentos/univesp/PI2/entrega-2026-11-02-bradley-rosto-natural/PaP_integral_gravacoes_PT_EN.mp4`.
  Inclui `Comparacao_King_Bradley_animada.mp4` (10 s, antes/depois ampliados),
  notas, validação e hashes. Fonte `2026-11-02-ursula-rosto-natural` preservada.
- Substituído o redimensionamento isolado dos lábios por deformação contínua
  do rosto original. Lábio inferior, queixo e mandíbula acompanham a abertura,
  com pequeno ajuste do bigode. Olhos, tapa-olho e cabelo mantidos: os 140
  primeiros pixels verticais do retrato normalizado são idênticos nas 61 poses.
  Transformação sem dobras; movimento suavizado pela energia da fala, sem
  alegação de sincronização fonética por visemas.
- Atualizadas as duas participações de Leonardo/King Bradley, incluindo a
  extensão ferroviária da primeira, e sua imagem na apresentação dos integrantes.
  **2.645 quadros** alterados dentro de blocos que somam **2.739 quadros**
  reencodificados. Os **14.762 quadros restantes são idênticos após decodificação**.
  Decodificação integral conferida e 15 amostras da composição exportada aprovadas.
- Áudio e duas faixas de legendas internos idênticos por hash dos fluxos;
  capítulos, timestamps e SRT/VTT preservados. Duração **09:43,367**, 17.501
  quadros, 1920 × 1080 a 30 fps. Correções da Úrsula e da voz do Bruno mantidas.
- Produção: `/home/avale/Documentos/univesp/PI2/producao_video/2026-11-02-bradley-rosto-natural/`.
  Entrega e arquivos de produção publicados e verificados por hash. Sem mudanças
  no aplicativo ou testes dele nesta etapa; documentação de continuidade atualizada.

## Vídeo — mapas coloridos em 02/11/2026

- Entrega: `/home/avale/Documentos/univesp/PI2/entrega-2026-11-02-mapas-coloridos/PaP_integral_gravacoes_PT_EN.mp4`.
  Inclui comparação animada de 7 s, imagem antes/depois, notas, validação e
  hashes. Fonte `2026-11-02-bradley-rosto-natural` preservada integralmente.
- A cena indicada perto de 04:51 usava “Pontos transparentes”, que aplica
  `grayscale(1)` à camada de mapa em `frontend/src/sao-paulo.css`. A captura
  antiga ativava esse modo; não era uma perda de cores na exportação.
- Capturas reais refeitas com o modo desativado: tema claro com filtro `none`;
  escuro com `invert(1) hue-rotate(180deg) brightness(.8) saturate(.6)`, sem
  grayscale. Um rótulo por linha e ausência de erros JavaScript conferidos.
  Nenhuma regra do aplicativo alterada; demonstração da lâmpada/dimmer mantida.
- Atualizadas quatro cenas em **04:43,100–04:52,000** e
  **09:15,167–09:21,633**: 461 quadros modificados, 478 reencodificados.
  Os **17.023 quadros restantes são idênticos após decodificação**. Avatares
  recompostos com suas poses existentes, incluindo o King Bradley atualizado.
- Decodificação integral e 12 amostras da exportação conferidas. Na região de
  mapa medida no quadro 8.700, pixels com diferença entre canais RGB maior
  que 20 passaram de **1,35% para 31,88%**, confirmando cores na nova cena.
  Áudio e legendas internos idênticos por hash dos fluxos; SRT/VTT, capítulos
  e timestamps mantidos. Duração **09:43,367**, 17.501 quadros, 1080p, 30 fps.
- Produção: `/home/avale/Documentos/univesp/PI2/producao_video/2026-11-02-mapas-coloridos/`.
  Entrega e arquivos de produção verificados por hash. Somente documentação de
  continuidade atualizada no repositório; testes do aplicativo não reexecutados.

## Vídeo — baldeações em 02/11/2026

- Entrega: `/home/avale/Documentos/univesp/PI2/entrega-2026-11-02-baldeacoes/PaP_integral_gravacoes_PT_EN.mp4`.
  Inclui `Trecho_baldeacoes.mp4` (27,067 s), imagem da tabela, SRT/VTT PT/EN,
  notas, validação e hashes. Fonte `2026-11-02-mapas-coloridos` preservada.
- A pedido do responsável, “Custo” passou a “Baldeações” nas duas tabelas de
  desempenho. Narração e legendas dizem **baldeações ponderadas**: transferência
  interna ferroviária continua contando ⅓ e demais trocas 1, conforme as notas
  visuais. Valores medidos preservados; não reinterpretar como tarifa ou
  quantidade física não ponderada. Sem alteração do planejador ou aplicativo.
- Refeitos os dois parágrafos de Maurício, entre **379,700 e 406,133 s**, usando
  a mesma referência de voz sintética existente. Áudio anterior substituído,
  sem sobreposição. Uma tentativa omitiu 5,14 e foi descartada; a tomada aceita
  e a exportação foram conferidas por transcrição local Whisper large-v3.
  Segunda fala ajustada com `atempo=1.172142857143`, sem mudança de tom, para
  manter a duração. Não houve escuta humana nesta revisão.
- Atualizadas legendas PT 111–117 e EN 109–113; demais entradas SRT/VTT
  preservadas. As duas faixas internas correspondem aos novos SRT. PCM fora
  dos parágrafos idêntico antes da recodificação AAC 192 kbps; não alegar
  identidade global do áudio codificado. Trecho medido: −18,1 LUFS, pico −5,6 dBFS.
- `validate_final.py` e `validate_final_enriched.py --reuse-frame-hashes`:
  saída **0**, decodificação integral de vídeo/áudio aprovada, **8 amostras**
  visuais conferidas. **812 quadros** alterados em bloco de 939 reencodificados;
  **16.562 quadros restantes idênticos após decodificação**. Valores das tabelas
  e retrato preservados nas composições. Capítulos e timestamps do vídeo
  mantidos: **17.501 quadros, 09:43,367, 1080p, 30 fps**.
- Produção: `/home/avale/Documentos/univesp/PI2/producao_video/2026-11-02-baldeacoes/`;
  scripts, tomadas, transcrições, logs e evidências preservados. Entrega e
  produção publicadas e verificadas por hash. Próximo passo: revisão humana
  da fala e do trecho; usar esta entrega como fonte de novas alterações.
  Referência Git permanece `feat/busca-bidirecional`, `34a46f29`; nenhuma criação
  de commit. Somente este documento alterado no repositório nesta etapa;
  testes do aplicativo não reexecutados.

## Vídeo — identificação de mídia em 02/11/2026

- Entrega: `/home/avale/Documentos/univesp/PI2/entrega-2026-11-02-identificacao-midia/PaP_integral_gravacoes_PT_EN.mp4`.
  Inclui imagem dos quatro avisos, SRT/VTT, notas, validação e hashes. Fonte
  `2026-11-02-baldeacoes` preservada integralmente; correções anteriores mantidas.
- Esclarecimento do responsável: a imagem de Maurício é uma fotografia com
  recorte e ajuste de luminosidade, não uma imagem gerada por IA. Removida a
  expressão ambígua “Fotografia e voz sintética”; novo aviso:
  **“Áudio gerado artificialmente”**. Para Leonardo, Ingrid e Nathalia:
  **“Imagem e áudio gerados artificialmente”**, conforme solicitado.
- Atualizados os quatro cartões iniciais, respeitando seus instantes de
  revelação, e nove intervalos de participações. Aviso incluído nas participações
  posteriores antes sem identificação. Imagens, animações e nomes preservados;
  nenhuma nova síntese de imagem ou áudio. Datas exibidas não alteradas nesta
  etapa; a conversa anterior recomendou sua retirada, mas não a executou.
- `validate.py`: saída **0**, decodificação integral aprovada, **32 amostras**
  exportadas conferidas. `check_graphics.py`: saída **0**, somente regiões dos
  avisos alteradas nas composições e diferença local da exportação conferida.
  **9.340 quadros** alterados em blocos de **9.637 reencodificados**; os
  **7.864 restantes são idênticos após decodificação**.
- Áudio e duas faixas internas de legendas idênticos por hash dos fluxos;
  SRT/VTT, capítulos e timestamps preservados. **09:43,367**, **17.501 quadros**,
  1920 × 1080, 30 fps. Produção e evidências:
  `/home/avale/Documentos/univesp/PI2/producao_video/2026-11-02-identificacao-midia/`.
  Entrega e produção publicadas e verificadas por hash; usar esta versão como
  fonte das próximas alterações. Branch `feat/busca-bidirecional`, HEAD
  `34a46f29`, sem novo commit. Somente continuidade alterada no repositório;
  testes do aplicativo não reexecutados.

## Vídeo — Arlequina completa em 02/11/2026

- Entrega: `/home/avale/Documentos/univesp/PI2/entrega-2026-11-02-arlequina-completa/PaP_integral_gravacoes_PT_EN.mp4`.
  Inclui `Comparacao_Arlequina.mp4` (8 s, antes/depois em slide e mapa), imagem
  comparativa, SRT/VTT, notas, validação e hashes. Fonte
  `2026-11-02-identificacao-midia` preservada integralmente.
- O chapéu já estava completo em `2026-10-28-procopio-madara/referencias/arlequina-avatar.png`;
  o normalizador cortava a imagem ao limitá-la a 360 × 270. Mantida a escala
  anterior do rosto, ampliada a área de composição para 540 × 330, deslocando
  a personagem 35 px à esquerda e 8 para baixo. Pontas dentro do vídeo e
  afastadas do rótulo ferroviário. Cartão inicial e silhueta também corrigidos.
- Barra branca removida restaurando o fundo dos slides; nas cenas de mapa e
  feedback, usadas as capturas reais correspondentes. Nenhuma imagem nova
  gerada. O aviso “Imagem e áudio gerados artificialmente” permanece visível.
- Substituída a boca isolada sobre cor fixa por deformação contínua do lábio
  inferior, queixo e mandíbula: **61 poses**, sem dobras, chapéu/olhos estáveis,
  excursão máxima do queixo de **19,51 px** entre poses extremas. Movimento
  suavizado pela energia da voz; não é sincronização fonética por visemas.
- **2.072 quadros** alterados/reencodificados: 710–1487 e 15555–16848. Os
  **15.429 restantes idênticos após decodificação**. Decodificação integral,
  **20 amostras** exportadas e remoção da barra em cinco amostras conferidas.
  Primeira execução do validador produziu relatório completo e depois saída
  143; confirmação `validate.py --reuse-frame-hashes`, vinculada aos hashes
  dos arquivos, terminou com **saída 0**. Logs preservados.
- Áudio e duas faixas internas de legendas idênticos por hash; SRT/VTT,
  capítulos e timestamps mantidos. **09:43,367**, **17.501 quadros**, 1080p,
  30 fps. Produção: `/home/avale/Documentos/univesp/PI2/producao_video/2026-11-02-arlequina-completa/`.
  Entrega, poses e scripts publicados e verificados por hash. Próximo passo:
  revisão humana da comparação animada; usar esta entrega nas próximas edições.
  Branch `feat/busca-bidirecional`, HEAD `34a46f29`, sem commit novo. Somente
  continuidade alterada no repositório; testes do aplicativo não reexecutados.

## Vídeo — iluminação da Ariana em 02/11/2026

- Entrega: `/home/avale/Documentos/univesp/PI2/entrega-2026-11-02-ariana-luz-normalizada/PaP_integral_gravacoes_PT_EN.mp4`.
  Inclui `Comparacao_luz_Ariana.mp4` (14 s lado a lado), imagem comparativa,
  SRT/VTT, notas, validação e hashes. Fonte `2026-11-02-arlequina-completa`
  preservada integralmente; todas as revisões anteriores mantidas.
- Diagnosticadas mudanças de luminosidade entre tomadas da Ariana no recorte
  original `2026-11-01-padronizacao-final/human-1.mkv`, especialmente em
  **00:57,667**. Curva luminosa fixa por tomada, referenciada na tomada estável
  entre 01:23,500 e 02:01,267; quatro tomadas ajustadas. Fator comum aos canais
  RGB e limite de branco, alfa original preservado. Não há controle de ganho
  automático a cada quadro nem nova síntese de imagem ou voz.
- Correção aplicada somente à apresentadora pela diferença entre retratos
  original/corrigido ponderada pelo alfa; pixels de fundo preservados antes da
  codificação. Movimentos, enquadramento, mapas, textos e sincronismo mantidos.
  Na medição de pele no **MP4 exportado**, os saltos de luminância RGB nos cortes
  de 57,667 / 67,467 / 83,500 / 121,267 s passaram, em módulo, de
  **34,02 / 6,06 / 7,17 / 6,09** para **0,89 / 1,50 / 0,39 / 1,65**.
  Escala RGB 0–255, não medida física de iluminação; medianas de 15 quadros
  antes/depois de cada corte. `check_exposure.py`: quatro verificações aprovadas.
- **1.450 quadros** alterados, em blocos de **1.779 reencodificados**;
  **15.722 restantes idênticos após decodificação**. Decodificação integral e
  **17 amostras** exportadas conferidas. Primeira execução gerou relatório
  completo, mas terminou com saída 143; confirmação
  `validate.py --reuse-frame-hashes`, vinculada aos hashes dos vídeos, saiu **0**.
- Áudio e duas faixas internas de legendas idênticos por hash; SRT/VTT,
  capítulos e timestamps preservados: **09:43,367**, **17.501 quadros**, 1080p,
  30 fps. Produção: `/home/avale/Documentos/univesp/PI2/producao_video/2026-11-02-ariana-luz-normalizada/`.
  Entrega e produção publicadas e conferidas por hash. Próximo passo: revisão
  humana da comparação; usar esta entrega como fonte de novas edições.
  Branch `feat/busca-bidirecional`, HEAD `34a46f29`, sem commit novo. Somente
  continuidade alterada no repositório; testes do aplicativo não reexecutados.

## Vídeo — qualidade geral em 02/11/2026

- Entrega: `/home/avale/Documentos/univesp/PI2/entrega-2026-11-02-qualidade-geral/PaP_integral_gravacoes_PT_EN.mp4`.
  Inclui `Comparacao_qualidade.mp4` (16 s lado a lado), imagem comparativa,
  SRT/VTT, notas, validação e hashes. Fonte `2026-11-02-ariana-luz-normalizada`
  preservada; todas as correções de conteúdo e iluminação mantidas.
- O responsável escolheu melhoria geral do vídeo final. Consultadas fontes de
  resoluções distintas e comparadas duas intensidades de tratamento. Escolhida
  a leve: `hqdn3d=0.5:0.35:0.0001:0.0001,unsharp=5:5:0.35:3:3:0`.
  Limiares temporais praticamente nulos evitam os padrões implícitos do filtro;
  redução de ruído essencialmente espacial e nitidez apenas na luminância.
- Exportação H.264 `libx264`, preset `slow`, CRF **14**, 1920 × 1080, 30 fps,
  aproximadamente **74,6 MB**. Sem ampliação de resolução, interpolação de
  quadros ou geração de detalhes de rostos. Melhoria visual suave, limitada pelas
  fontes; não afirmar recuperação de detalhe nativo. Gravações originais
  consultadas, mas não reeditadas nem substituídas nesta etapa.
- `validate.py`: **saída 0**, decodificação integral de **17.501 quadros**,
  **17 amostras** conferidas contra a referência filtrada. Maior erro absoluto
  médio da codificação nas amostras: **1,0004/255**; maior alteração da média
  de um canal RGB versus fonte: **0,439/255**. Métricas de fidelidade técnica,
  não uma escala absoluta de qualidade perceptiva. Vídeo inteiro recodificado;
  não alegar identidade de pixels com a fonte.
- Áudio e duas faixas internas de legendas idênticos por hash; SRT/VTT,
  capítulos e timestamps de apresentação mantidos, duração **09:43,367**.
  Produção: `/home/avale/Documentos/univesp/PI2/producao_video/2026-11-02-qualidade-geral/`.
  Entrega e produção publicadas e verificadas por hash. Próximo passo: avaliar a
  comparação em tamanho real; para novas edições de conteúdo, preferir a fonte
  anterior ao tratamento e reaplicar este acabamento uma única vez, evitando
  nitidez cumulativa. Branch `feat/busca-bidirecional`, HEAD `34a46f29`, sem novo
  commit. Somente continuidade alterada no repositório; testes do aplicativo
  não reexecutados.

## Vídeo — nome da Nathalia e legenda em 02/11/2026

- Entrega: `/home/avale/Documentos/univesp/PI2/entrega-2026-11-02-nathalia-legenda/PaP_integral_gravacoes_PT_EN.mp4`.
  Fonte `entrega-2026-11-02-qualidade-geral` preservada por SHA-256.
- Nome “Nathalia” centralizado nos limites visíveis do avatar: centro horizontal
  passou de 1740 para 1656 px, mantendo fonte, tamanho e posição do avatar.
  Alteração nas participações de 08:38,500 a 09:21,633 (quadros 15555–16848).
  Cartão inicial com nome completo mantém sua composição própria.
- Legenda PT 158, 09:02,622–09:06,938: quebra antes de “mais”, iniciando a
  segunda linha com “mais próximas”. Atualizados fluxo interno e SRT/VTT;
  palavras, tempos e fala preservados. Legenda inglesa inalterada.
- `validate.py`: saída 0; decodificação integral de 17.501 quadros aprovada,
  16.207 quadros fora do bloco idênticos após decodificação, 1.294 reencodificados
  em H.264 slow/CRF 14, sem reaplicar nitidez. Áudio e legenda inglesa idênticos
  por hash; 12 capítulos e duração de 09:43,367 mantidos. Faixa PT extraída
  difere apenas pela quebra solicitada; amostras de slide e mapas conferidas.
- Entrega inclui prévia, notas, validação e hashes; cópias publicadas verificadas.
  Produção: `/home/avale/Documentos/univesp/PI2/producao_video/2026-11-02-nathalia-legenda/`.
  Logs locais em `.cache/setup/nathalia-alinhamento-20261102/v2/`.
  Primeira composição local preservada como rascunho; a segunda evita amostrar
  a borda lateral do mapa ao restaurar o fundo do nome.
- Branch `feat/busca-bidirecional`, HEAD `34a46f29`, sem commit. Nenhuma alteração
  no aplicativo, bancos, relatório ou configurações globais. Testes do aplicativo
  não reexecutados. Esta entrega foi a fonte da revisão do percentual abaixo.

## Vídeo mais recente — percentual do Caio em 02/11/2026

- Entrega: `/home/avale/Documentos/univesp/PI2/entrega-2026-11-02-caio-997/PaP_integral_gravacoes_PT_EN.mp4`.
  Fonte `entrega-2026-11-02-nathalia-legenda` preservada por SHA-256;
  nova entrega publicada e cópias verificadas por hash.
- Arredondado **99,666% → 99,7%** na fala, no quadro de cobertura estrutural
  (05:33,100–05:48,800) e nas legendas internas e externas PT/EN, SRT/VTT.
  Contagens do censo e relatório preservados; trata-se de apresentação arredondada.
- Ressintetizada apenas a expressão numérica, **05:36,680–05:39,320**, com
  OmniVoice local e a referência existente da voz do Caio (`procopio-ref.wav`).
  Substituição sem sobreposição de vozes, RMS ativo igualado e bordas de 5 ms.
  PCM fora desse intervalo idêntico antes da recodificação da faixa em AAC
  192 kbit/s. Gravação visual preservada, sem nova animação labial.
- `transcribe.py exportado.wav`, Whisper large-v3 local: saída 0; reconheceu
  “O censo encontrou cobertura estrutural em 99,7% dos pares. Isso não garante
  viagem em qualquer horário.” Verificação automática, sem revisão auditiva humana.
- `python3 .cache/setup/caio-997-20261102/validate.py`: saída 0 no registro
  `validate-v3.log`; decodificação integral de **17.501 quadros** e áudio aprovada.
  **16.797 quadros** fora do bloco idênticos após decodificação; **704**
  reencodificados em H.264 slow/CRF 14. Sem reaplicar nitidez. Preservados
  1920 × 1080, 30 fps, 09:43,367, 12 capítulos e tempos das legendas.
  Diferenças textuais limitadas ao percentual; quebra da Nathalia mantida.
  Prévia e limites da cena conferidos. Composição final reutiliza glifos do
  próprio quadro, com `render_v3.py` e `mux_v3.py`; rascunhos locais preservados.
- Produção: `/home/avale/Documentos/univesp/PI2/producao_video/2026-11-02-caio-997/`.
  Logs locais: `.cache/setup/caio-997-20261102/`. Entrega inclui notas,
  prévia, `validacao.json` e `SHA256SUMS`. SHA-256 do vídeo:
  `15b1d613447022c7bb38d2eb6dbfa33429088733a5477f59140e508b72c7fb52`.
- Branch `feat/busca-bidirecional`, HEAD `34a46f29`, sem commit. Somente este
  estado alterado no repositório nesta etapa; aplicativo, bancos, relatório,
  sessões anteriores e configurações globais preservados. Testes do aplicativo
  não reexecutados. Usar esta entrega como fonte da próxima edição.
