# Estado do projeto para continuidade

Atualizado em **07/11/2026**, data de referência `America/Sao_Paulo`.

## Consolidação autorizada na main

O responsável autorizou commits, pushes e merges e confirmou que o destino é
`main`, não uma nova `master`. Base: `main` em `9c1191b`; desenvolvimento em
`feat/busca-bidirecional`/`c74e68f`; relatório em `relatorio`/`8f6fb3a`.
Esta árvore integra o desenvolvimento e o relatório, preservando seus históricos.
`sptrans`/`58e9982` e `feat/migracao-django-react`/`dd09f2e` já são ancestrais da base.
A publicação final deve ser conferida pelo hash de `origin/main`, não inferida
somente da presença deste documento. Nenhuma implantação acompanha o merge.

Os quatro conflitos eram `.gitattributes`, `.gitignore`, `AGENTS.md` e este estado.
Foram unidas as regras de atributos; preservadas as exclusões mais completas e
as instruções gerais de continuidade. A restrição antiga do AGENTS acadêmico
à branch `relatorio` foi superada pela autorização explícita de centralização.
O código da aplicação permanece idêntico ao de `c74e68f`; os arquivos acadêmicos
permanecem idênticos aos de `8f6fb3a`. Não houve correções funcionais nesta etapa.

Os estados anteriores foram preservados como registros históricos:
[desenvolvimento e mídias](CODEX_STATE_DESENVOLVIMENTO_2026-11-03.md) e
[relatório](CODEX_STATE_RELATORIO_2026-11-03.md). Expressões “sem commit” nesses
registros descrevem etapas passadas; consultar Git para a situação atual.

O fetch no repositório original falhou por referência interna inválida em
`refs/codex/`, já registrada em 02/11. Usado clone isolado em
`/tmp/pap-consolidacao-20261107`, sem apagar a referência nem limpar worktrees.
Na inspeção inicial não havia alterações rastreadas; um arquivo `:memory:.ses`
e 719 arquivos históricos não rastreados no worktree acadêmico foram preservados
fora da publicação, conforme a decisão anterior. Bancos, caches, credenciais e
mídias externas continuam locais. A pasta antiga `/tmp/pap-main-integracao`
estava ausente; seu registro de worktree não foi removido.

## Validação desta integração

- `npm --prefix frontend test`: saída 0, **15 aprovados**, zero falhas/ignorados,
  no desenvolvimento original; identidade do código com a integração conferida.
- `npm --prefix frontend run build`: saída 0 no clone integrado; aviso de bundle
  maior que 500 kB permanece, sem falha de compilação.
- `XDG_STATE_HOME=<logs>/test-state .venv/bin/python backend/manage.py test transit --noinput`:
  **501 testes, 499 aprovados e 2 falhas**, saída 1 no clone integrado. Falham
  `test_early_walk_preserves_later_faster_bus_and_final_status` e
  `test_progressive_yields_before_pedestrian_requests_and_can_close`, ambos já
  registrados em 02/11. O terceiro caso histórico de concorrência passou nesta
  execução; não foi corrigido e não se conclui que seja estável.
- Primeira execução no sandbox: 501 testes, 3 falhas de concorrência e 2 erros
  ambientais (socket bloqueado e diretório de exportação somente leitura).
  Repetição com sockets locais permitidos e estado descartável eliminou esses
  dois erros. **A suíte backend não está integralmente aprovada.**
- `git diff --cached --check` acusa cinco ocorrências históricas: linha vazia
  final em `caso_rotas_sobrepostas.tex` e quatro espaços finais em
  `revisao-2026-10-22/validacao.txt`. Bytes acadêmicos preservados; verificação
  restrita aos arquivos de controle/continuidade sem erros.
- Links locais do resumo e identidades das árvores conferidos antes do commit.
  Logs completos locais em
  `.cache/setup/consolidacao-20261107-dk4e2s40/` no repositório original.
  Não foram executados Playwright, suíte pública `mbm`, recompilação do relatório,
  importações, materializações, recargas de serviço nem testes do túnel público.

## Entregas e execução

- [Relatório final](relatorio_final/PaP_relatorio_2026-11-03_ENTREGA_correcao_materializacao.pdf):
  168 páginas, 4.901.874 bytes; [auditoria original](relatorio_final/correcao-materializacao-2026-11-03/VERIFICACAO.md).
  PDF e fontes preservados; envio institucional continua sem evidência nesta etapa.
- Vídeo definitivo informado: https://www.youtube.com/watch?v=rSvuIWx8QAg.
  Fontes e MP4 de 03/11 ficam fora do Git; caminhos, hashes e limites estão no
  histórico de desenvolvimento. Disponibilidade do YouTube não revalidada.
- Aplicação Django + React/Vite/Leaflet; GTFS e materializações SQLite separados
  do banco Django. Configuração pública Gunicorn/Cloudflare separa administração.
  O último teste público documentado é de 03/11; não inferir funcionamento atual
  do túnel temporário. Preservar instâncias e dados existentes.

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

## Pendências e próximo passo

Investigar os testes de concorrência identificados acima e executar as validações
pública e de navegador antes de declarar a suíte completa aprovada. Manter as
limitações de cobertura municipal, horários ARTESP interpolados e calendário,
verificação presencial com passageiros, QR físico e exigências institucionais;
ver históricos e [auditoria de Mauá](maua-artesp-audit-20261102.md).

Após publicar, conferir que todas as pontas de branches estão contidas em
`origin/main`. Não apagar branches, worktrees, dados nem referências internas
como efeito colateral da consolidação. Ao retomar, conferir Git e ler
[AGENTS.md](../AGENTS.md) e [procedimento de continuidade](CODEX_CONTINUITY.md).
