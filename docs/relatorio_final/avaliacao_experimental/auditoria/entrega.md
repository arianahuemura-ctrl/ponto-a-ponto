# Entrega EXP-1 — 28/10/2026
## Escopo executado
Preparação operacional, não execução dos experimentos. Auditoria estática do código, documentos acadêmicos existentes, cabeçalhos de instrumentos e metadados de evidências. Seleção de cenários usando somente dados públicos de transporte em SQLite somente leitura. Nenhuma consulta a bancos privados de pesquisa, mensagens, replays ou capturas pessoais.

| Entrega | Arquivos principais | Estado |
|---|---|---|
| Matriz e dependências | matriz_avaliacoes.csv, dependencias.csv | Consolidação de fontes e pendências |
| MAN/QR | qr_man.md, privacidade.md | Oito vagas planejadas; sem recrutamento |
| Registro | ficha canônica existente; formularios/*.csv e instrumentos.xlsx | Modelos vazios e ordem planejada |
| Telemetria | indicadores_telemetria.csv, telemetria.md, schemas/evento_normalizado.json | Observáveis, ambiguidades e minimização |
| Benchmark | benchmark.md, benchmark/cenarios.csv, configuracao_modelo.json | Nove cenários candidatos; qualificação pendente |
| Análise | analise.md, modelos_resultados/*, scripts/* | Scripts descritivos e modelos sem resultados |
| Rastreabilidade | rastreabilidade.md, manifesto_modelo.json, scripts/manifesto.py | Modelo por execução e inventário SHA-256 |
| Integração futura | integracao_academica.md | Proposta; PDF não alterado |
| Auditoria | auditoria/*, testes/test_instrumentos.py | Verificações artificiais documentadas |

A única alteração em instrumento preexistente é o cabeçalho de estudo_ihc_ampliado/ficha_coleta_vazia.csv. O anterior está arquivado aqui, somente para rastreabilidade. Nenhuma linha coletada existia nessa ficha; demais instrumentos históricos foram preservados.

## Validação
23 testes unitários passaram, sem importar/executar o aplicativo. Foram verificados pareamento, ausências, falhas, relógios, segmentação, supressão de células, procedência, restauração dos hooks, fixtures sem acesso à rede, integridade e censura no benchmark. As CLIs de análise foram exercitadas com CSVs artificiais; três gráficos pareados e cinco gráficos técnicos gerados apenas em /tmp/ARTIFICIAL-PAP-validacao-EXP1. Os 21 modelos/abas da planilha foram reabertos e conferidos: sem registros de resultados. Oito vagas planejadas não são participantes.

O modelo de prontidão retorna bloqueio, como esperado. Compatibilidade real dos hooks, isolamento, QR no celular, gabaritos múltiplos e fixtures dependem de piloto futuro. Não foi executado benchmark, materialização nem ensaio com participantes. Modelos gráficos adicionais são especificações de apresentação, não gráficos com resultados.

PDF preservado: relatorio_final_pi2_v2.pdf, 133 páginas, MD5 cc9f063ec8ae7b225bdf0463d764cd19, compilação anterior em 28/10/2026 às 13:08:50 -03. Não se recompilou porque o conteúdo acadêmico não mudou. O diff preexistente permaneceu idêntico; as 16 fontes de aplicação auditadas conservaram SHA-256. Nenhum documento assinado, banco, captura ou outro worktree foi modificado.

## Dependências efetivas
Consentimento e responsável; autorização específica para telemetria real; qualificação dos cenários/gabaritos e serviço; verificação do QR no celular; respostas externas e relógio congelados; isolamento, cache e bloqueio de rede; piloto de compatibilidade/procedência; retenção/exclusão operacionais. Não preencher lacunas com números hipotéticos. Não estender resultados de São Paulo à operação em Mauá.

O estado final do Git e os hashes da entrega ficam em validacao_final.json e inventario_entrega.json. Branch relatorio; alterações preexistentes preservadas; sem commit, merge, rebase ou reset.
