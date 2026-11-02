# Comparação de desempenho após streaming concorrente

Método: repetir exatamente as 3.264 combinações de origem, destino e horário
registradas no levantamento anterior, com 32 processos. Preservar os quatro
lotes dos grupos anteriormente instáveis, sem seleção adaptativa de uma nova
amostra. Horários simulados: 03/11/2026 às 08:00, 14:00 e 02:00.

A aplicação atual é executada sem modificações funcionais pelo teste. Assim
como antes, chamadas externas são bloqueadas e não são tratados como medidos
os tempos de rede, túnel e navegador. Agora, uma tentativa externa em uma
thread não impede que outra publique uma primeira rota; essa tentativa é
contada separadamente. Sem rota e com tentativa externa, o resultado permanece
indeterminado (`external_required`). O teto experimental é de 30 segundos.

Depois de fechar cada consulta, o teste aguarda os produtores cancelados fora
da medição da primeira rota, antes de começar o próximo caso no mesmo processo.
Isso evita trabalho remanescente contaminando o teste seguinte. Os pools são
recriados, mantendo seus limites de quatro e oito threads. GTFS permanece
carregado; cache de resposta é esvaziado a cada caso. O leitor materializado
isolado também é medido, depois da consulta principal, como no levantamento
anterior. Não é uma medição de latência de um celular nem de fila de produção.

Comparações principais: casos que tiveram rota nos dois testes; casos que
passaram a receber rota; regressões de disponibilidade; medianas/P95 por tipo,
horário e custo anterior da rota, além de cumprimento do limite de 30 segundos.


## Resultados

Foram repetidas as 3.264 consultas, sem alteração dos três bancos de dados. A comparação pareada inclui somente os casos que entregaram rota em até 30 s nos dois levantamentos; ganhos e perdas de disponibilidade são contados separadamente.

| Resultado | Antes | Depois |
|---|---:|---:|
| external_required | 936 | 839 |
| first_route | 1652 | 1728 |
| no_route_completed | 676 | 697 |

Casos com primeira rota nos dois testes: 1637. Passaram a receber rota: 91. Não reproduziram o sucesso anterior: 15. As diferenças de disponibilidade não são atribuídas automaticamente à alteração: buscas com orçamento interno dependem de carga/cache e chamadas externas continuam bloqueadas.

| Horário | Pares com sucesso em ambos | Mediana antes | Mediana depois | P95 antes | P95 depois |
|---|---:|---:|---:|---:|---:|
| 08:00 | 557 | 0.308 s | 0.602 s | 5.760 s | 5.215 s |
| 14:00 | 561 | 0.280 s | 0.604 s | 5.766 s | 5.204 s |
| 02:00 | 519 | 0.253 s | 0.590 s | 0.739 s | 1.281 s |

### Custo da primeira rota do teste anterior

A classificação usa o custo anterior para manter os mesmos pares em cada grupo; a alternativa entregue agora pode ser diferente.

| Custo | Pares com sucesso em ambos | Mediana antes | Mediana depois | P95 antes | P95 depois |
|---|---:|---:|---:|---:|---:|
| 0 | 363 | 0.318 s | 0.553 s | 0.567 s | 0.854 s |
| 1 | 328 | 0.332 s | 0.680 s | 0.637 s | 1.041 s |
| 2 | 339 | 0.349 s | 0.756 s | 5.755 s | 5.095 s |
| 3 | 89 | 5.644 s | 5.143 s | 7.202 s | 5.655 s |
| 4 | 41 | 5.747 s | 5.216 s | 8.298 s | 5.716 s |

### Materialização disponível antes da dependência externa

Dos 89 casos em que o fluxo antigo parava na dependência externa, apesar de uma opção materializada disponível, 89 entregaram rota no novo fluxo. Mediana 0.601 s, P95 1.032 s, máximo 1.260 s.

Falhas internas de fontes: 0. Saturações: 0. Primeiras rotas entregues apesar de tentativa externa concorrente: 110.

### Evidências

- [Comparação completa em JSON](../artifacts/benchmarks/async-comparison-20261101/comparison.json).
- [Resultados pareados em CSV](../artifacts/benchmarks/async-comparison-20261101/paired-results.csv).
- [Medições individuais](../artifacts/benchmarks/async-comparison-20261101/latency-results.jsonl).

Os grupos são deliberadamente heterogêneos e incluem muitos pares problemáticos. Não se estima uma taxa de sucesso municipal. A medição usa 32 processos simultâneos e exclui a latência do roteador externo, HTTP e celular. A remoção de uma espera sequencial não implica que toda primeira rota deva ficar abaixo de um segundo.


## Conclusão

A entrega deixou de ser bloqueada pela dependência pedestre nos 89 casos
identificados. Todas as 1.264 consultas que tinham uma opção materializada
válida no leitor isolado anterior receberam rota no novo fluxo: mediana de
0,649 s, P95 de 1,045 s e máximo de 2,335 s.

A mudança não resolveu toda a latência: nos 1.637 cenários com sucesso nos dois
testes, a mediana aumentou de 0,282 para 0,599 s, enquanto o P95 caiu de 5,698
para 5,143 s e o máximo caiu de 10,712 para 5,936 s. A publicação concorrente
reduziu as maiores esperas, mas consultas antes rápidas ficaram mais lentas
sob carga. O próximo ajuste a investigar é priorizar a materialização antes
de disputar processamento com as buscas pesadas, mantendo publicação assíncrona.
A medição não isolou quantitativamente o efeito de CPU, cache e escalonamento.

Houve ganho líquido de 76 consultas com rota: 91 passaram a responder, enquanto
15 sucessos anteriores não se reproduziram. Destes 15, 12 passaram a depender
de uma chamada externa não medida e três terminaram sem rota com busca limitada.
Todos pertenciam ao grupo com resposta anterior acima de cinco segundos.
Não houve perda de sucesso entre os casos com opção materializada válida.

As 1.728 primeiras rotas entregues ficaram abaixo de seis segundos no teste
local. Isso não garante o prazo de 30 segundos no celular: 839 consultas ainda
dependem de serviço externo não medido, e 697 terminaram sem rota.
