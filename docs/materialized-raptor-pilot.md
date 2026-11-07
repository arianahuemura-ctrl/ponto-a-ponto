# Piloto de composição de duas materializações — 01/11/2026

Execução somente leitura; nenhum registro de rota foi publicado e o limite do
aplicativo continua inalterado. O par dirigido 9112409 → 5614789 não possui
entrada em paths, expanded_paths, topup_paths nem short_walk_paths.

O localizador determinístico examina até 2.000 pontos de conexão para um par
vazio com embarque e desembarque cadastrados. Respeita a prioridade das tabelas,
rejeita repetição de linhas e filtra serviços sem partida próxima às 08:00.
Escolhe a menor soma de tempos estruturais entre os candidatos examinados.
Isso é uma heurística de seleção, sem garantia de ótimo global.

A combinação escolhida usa Pinheiros Metrô (6311287): primeiro trecho de custo
2, segundo de custo 3, conexão ferroviária interna de custo 1/3. Total 16/3,
com sete embarques e seis trocas físicas. Sequência: 271M-10 → 271C-10 → Linha 4
→ Linha 9 → 6091-10 → 6072-10 → 6L07-10. Caminhadas somam 2.335,17 m; o limite
300 m de uma caminhada direta não limita a soma das caminhadas de uma viagem.

Foi executado o weighted_planner real, com teto 8, em um grafo em memória
restrito aos segmentos embarque/desembarque das duas materializações e suas
caminhadas verificadas. Os intervalos das frequências foram deslocados para o
início de cada segmento. A avaliação independente da concatenação exata e o
RAPTOR produziram as mesmas linhas, pontos, chegada e custo. Asserções conferem
a equivalência e a ausência de interrupção por prazo nos três horários.

Resultados do domingo 01/11/2026, segundo os horários e estimativas cadastrados:

| Saída | Chegada | Duração estimada |
| --- | --- | --- |
| 08:00 | 12:31:12 | 271,2 min |
| 12:00 | 16:34:53 | 274,9 min |
| 18:00 | 22:46:12 | 286,2 min |

A busca do ponto de conexão levou 3,64 s, a carga da rede aproximadamente
0,3 s e o RAPTOR restrito aproximadamente 1 ms por horário. A avaliação exata,
incluindo calendários da rede, levou cerca de 20 ms. Estes tempos não estimam
uma busca RAPTOR integral nem uma materialização de todos os pares. Geometrias
foram omitidas no piloto; nenhuma requisição externa foi necessária.

O primeiro candidato testado tinha serviço apenas em dias úteis; outros usavam
linhas noturnas ou excediam o horizonte. Foram descartados. A conectividade
estrutural isolada não comprova viabilidade em determinado horário.

Reprodução, a partir da raiz:

```sh
.venv/bin/python scripts/experiments/find_materialized_composition.py
.venv/bin/python scripts/experiments/test_materialized_composition.py
```

Relatório: `artifacts/benchmarks/materialized-raptor-composition-20261101.json`.
O teste comprova um caso possível, não a cobertura completa: guardar cinco
subrotas por par pode descartar subrotas úteis para outras composições.
O RAPTOR original opera em rodadas sobre linhas; este piloto usa a implementação
ponderada existente sobre segmentos selecionados de rotas materializadas:
https://www.microsoft.com/en-us/research/publication/round-based-public-transit-routing/
