# Cobertura e tempo até a primeira rota — levantamento de 01/11/2026

Censo exaustivo dos pares distintos e amostragem adaptativa do fluxo local de consulta. Foram usados 32 processos simultâneos. Os cenários representam 03/11/2026, terça-feira, em America/Sao_Paulo: 08:00, 14:00 e 02:00. Não se alterou o aplicativo nem as materializações.

## Censo completo

Dos 496.108.802 pares direcionais, **494.451.148 têm materialização (99,6659%)** e **1.657.654 não têm**. O censo varreu 573.074.566 registros das quatro tabelas em 27.55 s. Esse tempo é de processamento em lote, não de resposta a um passageiro.

| Rotas por par | Pares |
|---:|---:|
| 0 | 1.657.654 |
| 1 | 15.078 |
| 2 | 19.879 |
| 3 | 11.646 |
| 4 | 13.291 |
| 5 | 494.391.254 |

## Auditoria de acesso

Foram examinados individualmente os 50 pontos sem saída e os nove sem chegada. Todos os 50 primeiros aparecem somente na última posição das viagens em que constam. Todos possuem caminhada externa verificada até um ponto com embarque: a menor opção por ponto varia de 9,54 a 493,61 m. A política de materialização admite apenas integração interna antes do primeiro embarque, bloqueando esses acessos externos. Não é uma proibição oficial de embarque.

Os nove destinos aparecem somente na primeira posição das viagens. Oito tiveram todas as conexões pedestres rejeitadas pelo limite de encaixe de 20 m; os encaixes desses pontos vão de 21,65 a 40,45 m. O nono, parada 8313677, tem caminhada mínima calculada de 1.104,64 m, superior ao limite materializado de 1.000 m. Há diferença entre esse limite e o de revisão final do aplicativo (1.500 m), assim como entre os limites de encaixe local (20 m) e público (30 m). Não foi testado aqui se o mapa público oferece o mesmo percurso.

[Tabela individual dos 59 pontos](endpoint-audit-20261101.md). A classificação por acesso explica 1.313.444 pares ainda vazios; os outros 344.210 não foram declarados inacessíveis.

## Primeira rota e limite de 30 segundos

Foram executadas **3.264 consultas amostrais** em 512.3 s de execução dos dois ciclos sequenciais. Houve 1652 primeiras rotas, 936 interrupções ao necessitar de serviço externo não medido e 676 buscas terminadas sem rota. Das buscas sem rota, 660 atingiram limites internos de pesquisa; portanto continuam inconclusivas. Não houve erro de execução nem interrupção pelo teto experimental de 30 s.

Os tempos abaixo incluem somente os casos que entregaram uma rota. A amostra deliberadamente concentra pontos problemáticos e pares vazios: sua taxa de sucesso não representa a taxa de sucesso dos 496 milhões de pares.

| Cenário | Consultas | Com primeira rota | Mediana | P95 | Máximo |
|---|---:|---:|---:|---:|---:|
| Pico — 08:00 | 1088 | 563 | 0.308 s | 5.796 s | 10.620 s |
| Entrepico — 14:00 | 1088 | 566 | 0.283 s | 5.842 s | 10.712 s |
| Madrugada — 02:00 | 1088 | 523 | 0.255 s | 4.755 s | 10.393 s |

Todas as 1652 primeiras rotas medidas chegaram antes de 30 s. Isso **não comprova o limite de ponta a ponta**: HTTP, túnel, renderização e roteador pedestre público foram excluídos. Ao precisar de rede externa, o teste parou e registrou `external_required`, sem substituir a caminhada por linha reta nem considerar a interrupção como resposta útil.

Em **89 consultas**, o fluxo exigiu uma chamada externa antes de entregar rota, enquanto o leitor materializado isolado entregou uma opção. A mediana desse leitor foi 0.287 s e o máximo 0.530 s. A comparação isolada ocorre depois da consulta principal e pode aproveitar cache de geometria; ela identifica a dependência desnecessária, mas não estima exatamente a economia no celular.

## Regra adaptativa e quatro lotes

Cada lote tem 32 consultas distintas, executadas com 32 processos. Estabilidade: um único estado de saída e P90−P10 ≤ máximo de 50 ms e 20% da mediana. Grupos estáveis encerram após o lote; os demais chegaram a quatro lotes (128 consultas por grupo/horário). O quarto lote foi acrescentado em um segundo ciclo de processos, reaproveitando todos os resultados anteriores. O cache de respostas é esvaziado por consulta; GTFS permanece carregado e o cache de geometria varia naturalmente por processo.

Os três grupos/horários de caminhada materializada foram estáveis com primeira rota. Os três de pares próximos foram estáveis apenas quanto à interrupção para serviço externo: **seu tempo até a primeira rota continua desconhecido**. Os 24 demais grupos/horários continuaram heterogêneos após quatro lotes; não foram tratados como tendo tempo constante.

| Grupo | Hora | Consultas | Rotas entregues | Dependência externa | Sem rota | Lotes |
|---|---:|---:|---:|---:|---:|---:|
| Origem com acesso bloqueado | 08:00 | 128 | 0 | 88 | 40 | 4 |
| Origem com acesso bloqueado | 14:00 | 128 | 0 | 88 | 40 | 4 |
| Origem com acesso bloqueado | 02:00 | 128 | 0 | 82 | 46 | 4 |
| Ponto sinalizado ↔ ponto próximo | 08:00 | 128 | 90 | 38 | 0 | 4 |
| Ponto sinalizado ↔ ponto próximo | 14:00 | 128 | 90 | 38 | 0 | 4 |
| Ponto sinalizado ↔ ponto próximo | 02:00 | 128 | 90 | 38 | 0 | 4 |
| Destino com acesso bloqueado | 08:00 | 128 | 0 | 106 | 22 | 4 |
| Destino com acesso bloqueado | 14:00 | 128 | 0 | 107 | 21 | 4 |
| Destino com acesso bloqueado | 02:00 | 128 | 0 | 100 | 28 | 4 |
| Caminhada materializada | 08:00 | 32 | 32 | 0 | 0 | 1 |
| Caminhada materializada | 14:00 | 32 | 32 | 0 | 0 | 1 |
| Caminhada materializada | 02:00 | 32 | 32 | 0 | 0 | 1 |
| Par vazio com embarque/desembarque | 08:00 | 128 | 0 | 0 | 128 | 4 |
| Par vazio com embarque/desembarque | 14:00 | 128 | 0 | 0 | 128 | 4 |
| Par vazio com embarque/desembarque | 02:00 | 128 | 0 | 0 | 128 | 4 |
| Ônibus direto | 08:00 | 128 | 127 | 1 | 0 | 4 |
| Ônibus direto | 14:00 | 128 | 126 | 2 | 0 | 4 |
| Ônibus direto | 02:00 | 128 | 128 | 0 | 0 | 4 |
| Ônibus: uma baldeação | 08:00 | 128 | 120 | 8 | 0 | 4 |
| Ônibus: uma baldeação | 14:00 | 128 | 123 | 5 | 0 | 4 |
| Ônibus: uma baldeação | 02:00 | 128 | 122 | 6 | 0 | 4 |
| Ônibus: múltiplas baldeações | 08:00 | 128 | 92 | 30 | 6 | 4 |
| Ônibus: múltiplas baldeações | 14:00 | 128 | 93 | 30 | 5 | 4 |
| Ônibus: múltiplas baldeações | 02:00 | 128 | 67 | 32 | 29 | 4 |
| Par próximo com materialização | 08:00 | 32 | 0 | 32 | 0 | 1 |
| Par próximo com materialização | 14:00 | 32 | 0 | 32 | 0 | 1 |
| Par próximo com materialização | 02:00 | 32 | 0 | 32 | 0 | 1 |
| Ferroviário ou misto | 08:00 | 128 | 102 | 12 | 14 | 4 |
| Ferroviário ou misto | 14:00 | 128 | 102 | 12 | 14 | 4 |
| Ferroviário ou misto | 02:00 | 128 | 84 | 17 | 27 | 4 |

## Origem das respostas adicionais

Uma repetição diagnóstica de 123 consultas que haviam tido sucesso no fluxo completo, mas não no leitor materializado isolado, identificou as seguintes fontes. Não é um quinto lote de desempenho, e seus tempos não entram nas estatísticas acima.

| Fonte da primeira rota | Casos |
|---|---:|
| external_required | 27 |
| no_route_completed | 5 |
| raptor | 91 |

O RAPTOR foi confirmado em 91 consultas de 42 pares distintos da amostra. As outras 32 respostas não se reproduziram nesse replay: 27 pararam em dependência externa e cinco terminaram sem rota. A busca tem limites de tempo internos e o estado de cache/carga varia; não atribuímos essas 32 respostas originais a nenhum mecanismo.

Esse resultado impede concluir que o fallback se tornou dispensável apenas pela cobertura estrutural. A prioridade é entregar materializações válidas primeiro e usar busca complementar quando as sequências salvas não atendem ao horário. Não há estimativa global de quantos pares precisam do RAPTOR a partir desta amostra dirigida.

O fluxo multimodal também consulta o índice antigo de conexões. Uma resposta fora do leitor novo não pode ser atribuída automaticamente ao RAPTOR.

## Evidências e limites

- [Contrato e método](coverage-audit-contract.md).
- [Censo completo](../artifacts/benchmarks/coverage-audit-20261101/census-summary.json); os 32 arquivos `census-*.jsonl` registram as 22.274 origens.
- [Resultados das consultas](../artifacts/benchmarks/coverage-audit-20261101/latency-results.jsonl) e [resumo por grupo](../artifacts/benchmarks/coverage-audit-20261101/latency-summary.json).
- [Validação cruzada](../artifacts/benchmarks/coverage-audit-20261101/validation.json).
- Fontes e método não avaliam incidentes, trânsito real, lotação ou alterações posteriores ao cadastro local. Uma sequência materializada não garante serviço naquele horário. Nenhum teste de carga foi feito contra o roteador público.

O próximo ajuste fundamentado por este levantamento é servir uma rota materializada válida antes de aguardar caminhada externa e revisar as regras de acesso dos 59 pontos. A utilidade de cada fallback deve ser avaliada pela fonte real das respostas, preservando a distinção entre cobertura estrutural e disponibilidade no horário.
