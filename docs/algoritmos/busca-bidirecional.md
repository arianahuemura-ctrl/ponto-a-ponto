# Índice de conectividade e custo temporal

Implementação experimental da branch `feat/busca-bidirecional`. O fluxo de conexões 16/8/4 integra a interface para pares preparados;
o planejador anterior atende os demais casos. Veja o README da raiz para os comandos
`build_sptrans_connections` e `query_sptrans_connections`. Este documento descreve
o índice inicial e o comando legado `query_sptrans_graph`. O banco derivado é `sptrans.routing.sqlite3`, ao lado
do GTFS configurado em `SPTRANS_DATABASE`; os dois arquivos permanecem locais e
ignorados pelo Git. O GTFS de origem não é modificado.

## Estruturas persistentes

| Estrutura | Conteúdo |
| --- | --- |
| `graph_stop` | Paradas atendidas por ônibus, nome e coordenadas. |
| `pattern` | Linha, sentido, sequência de paradas, shape e projeções das paradas. |
| `timetable` | Viagens e seus calendários, horários/frequências; horários distintos não são colapsados. |
| `ride_edge` | Todos os pares ordenados de paradas alcançáveis no mesmo itinerário, índices de embarque/desembarque, distância e limite inferior do tempo a bordo. |
| `walk_edge` | Pares próximos direcionados; distância em linha reta para triagem, percurso verificado, distância real, tempo, fonte, data e estado. |
| `direct_adjacency` | Visão das conexões sem troca de ônibus. |
| `walk_adjacency` | Somente caminhadas verificadas dentro do limite. |
| `transfer_link` | Transferência no mesmo ponto (zero caminhada) ou caminhada verificada entre pontos distintos. |
| `routes_0`, `routes_1`, `routes_2` | Produtos relacionais para exatamente 0, 1 e 2 baldeações. |
| `candidate_cache` | Materialização por origem, destino e número de baldeações, invalidada quando as caminhadas mudam. |
| `graph_meta` | Origem/versão do GTFS, parâmetros, contadores de cobertura e revisão. |

Os índices `ride_out`, `ride_in` e `walk_in` permitem consultar tanto as saídas da
origem quanto as entradas do destino. Uma conexão A→B não implica B→A.

O equivalente ao dicionário solicitado pode ser consultado assim:

```sql
SELECT destination, distance_meters, pattern_id, boarding_index, alighting_index
FROM direct_adjacency WHERE origin = '1211364';

SELECT destination, distance_meters, seconds
FROM walk_adjacency WHERE origin = '1211364';
```

Um par pode ter mais de uma linha, sentido, distância e ocorrência no itinerário.
Essas opções são preservadas; não se reduz o par a um único custo estático.
Viagens com a mesma linha/sentido/shape/sequência compartilham as conexões, mantendo
seus próprios horários. Paradas repetidas em linhas circulares mantêm índices distintos.
As ligações de uma parada para ela mesma são omitidas.

## Distâncias e velocidades

Distâncias de ônibus são medidas ao longo do `shapes.txt`, entre projeções ordenadas
das paradas. A importação atual não mantém `shape_dist_traveled`; por isso o índice
projeta as paradas na geometria, respeitando sua ordem e tolerância de 150 m.
Se não houver projeção confiável, `distance_meters` é NULL: não se inventa uma
medida rodoviária a partir da distância em linha reta. O custo programado continua
podendo ser calculado pelos horários. Uma evolução útil é importar
`shape_dist_traveled`, quando fornecido consistentemente no GTFS.

A velocidade de caminhada do modelo é **4,5 km/h = 75 m/min = 1,25 m/s**:

```text
tempo_caminhada_segundos = distancia_do_percurso_metros / 1,25
450 m = 360 s = 6 min
```

O parâmetro está centralizado em `walking.py` e também foi aplicado no planejador
existente, na comparação de pontos próximos e na explicação da interface. As chaves
de cache de caminhadas e alternativas foram versionadas para não reutilizar tempos
calculados a 4 km/h. Trata-se de uma hipótese uniforme do modelo, não de uma
medição da velocidade de cada passageiro.

A distância em linha reta só seleciona candidatos. Apenas percursos a pé detalhados,
com extremos coerentes, distância finita, fonte e data, entram em `walk_adjacency`.
O tempo é recalculado pela velocidade do projeto, independentemente da duração
retornada pelo roteador. O limite padrão é 1.000 m de percurso por conexão.
Uma tentativa indisponível ou um percurso maior que o limite não cria conexão.
Não se presume que o trajeto inverso tenha a mesma distância.

## Combinação com baldeações

```text
0: ônibus A→D
1: ônibus A→X + transferência X→Y + ônibus Y→D
2: ônibus A→X + transferência X→Y + ônibus Y→Z
   + transferência Z→W + ônibus W→D
```

Transferências X→Y e Z→W podem ocorrer no mesmo ponto. Caminhar não conta como
nova condução. Cada novo embarque após o primeiro acrescenta uma baldeação e a
margem de 120 s já usada pelo planejador. Não se cria troca consecutiva para o
mesmo padrão de itinerário: permanecer no ônibus já é uma conexão direta.

As visões fazem o produto cartesiano **restrito por conexões existentes**, com
índices por origem/destino. Não se materializam globalmente todos os itinerários
com uma e duas baldeações: isso multiplicaria as linhas do banco e repetiria dados.
A primeira consulta materializa os candidatos desse par em `candidate_cache`.
Consultas seguintes reutilizam a topologia e recalculam os horários.

```sql
SELECT * FROM routes_0 WHERE origin='1211364' AND destination='6714560';
SELECT * FROM routes_1 WHERE origin='1211364' AND destination='6714560' LIMIT 100;
SELECT * FROM routes_2 WHERE origin='1211364' AND destination='6714560' LIMIT 100;
```

`lower_bound_seconds` soma os menores tempos programados a bordo, caminhadas e
margens de transferência. **Não inclui espera e não é o tempo final de viagem.**
Ele serve para podar candidatos que não melhoram a solução já encontrada.

## Consultar rotas e custo em tempo

```bash
python backend/manage.py build_sptrans_graph

python backend/manage.py query_sptrans_graph 1211364 6714560 \
  --at 2026-10-07T08:00:00-03:00 --transfers 0 1 2

# Caminhada inicial de 450 m: passageiro só estará pronto após 6 minutos.
python backend/manage.py query_sptrans_graph 1211364 6714560 \
  --at 2026-10-07T08:00:00-03:00 --transfers 0 --access-meters 450
```

`--access-meters` e `--egress-meters` devem ser distâncias de percursos a pé já
verificados, não separações em linha reta. Essa primeira versão consulta um par de
paradas; ainda não escolhe automaticamente os conjuntos de acesso/saída de um endereço.

A saída retorna a melhor opção encontrada para cada quantidade **exata** de
baldeações pedida, com linha, viagem, sentido, pontos intermediários, distâncias,
horários, espera, caminhada, margem e custo total. Uma categoria pode não ter rota
viável. A saída mantém alternativas mais lentas de outra categoria para permitir a
comparação; não é ainda a filtragem visual das alternativas da aplicação.

A avaliação considera o calendário e suas exceções, horários além de 24:00,
frequências exatas e não exatas, caminhada inicial e cada conexão. Para frequências
sem fase exata utiliza a espera média de meio intervalo, explicitada por
`frequency_estimate`. Dados Olho Vivo não são pré-calculados nem armazenados como
peso fixo: os custos dessa consulta são **programados/estimados**, não previsões
operacionais. Horizonte de embarque/percurso: seis horas, como no planejador atual.

Limites padrão por categoria: 10.000 candidatos e cinco segundos para a consulta
SQL (`--max-candidates`, `--query-seconds`). Esse limite de tempo é da enumeração
SQL, não de toda a avaliação temporal. Se algum limite interromper a enumeração,
`candidate_search_complete=false`; os candidatos truncados não são apresentados
como prova da rota ótima. `complete_for_verified_graph` se refere somente à rede
já verificada; consulte também `walk_coverage` e `walk_pairs_not_verified`.

## Completar a rede de caminhadas

A construção inicial não faz chamadas externas. Ela é transacional em um arquivo
temporário e só publica o índice ao terminar. Uma falha preserva o índice anterior.
A mudança do arquivo GTFS invalida o índice. Reconstruí-lo reinicia as verificações
a pé; exporte ou preserve os percursos a reutilizar e confira sua validade.

Para um pequeno lote pelo roteador já usado pela aplicação:

```bash
python backend/manage.py verify_sptrans_walks --origin 1211364 --limit 4
```

O limite padrão é zero; o comando respeita o limitador do provedor existente. As
próximas execuções selecionam candidatos ainda pendentes. Falhas ficam marcadas
como `unavailable` e podem ser substituídas por uma importação verificada posterior.

Para importar percursos de uma base/roteador de uso em lote:

```bash
python backend/manage.py verify_sptrans_walks --file percursos.jsonl
```

Cada linha contém `origin`, `destination` e `result`, no formato de `walking.route`:

```json
{"origin":"A","destination":"B","result":{"available":true,"distance_meters":450,"geometry":[[-23.55,-46.63],[-23.551,-46.632]],"source":"Roteador a pé / versão da base OSM"}}
```

As coordenadas devem corresponder aos pontos reais; o exemplo apenas ilustra o
formato. Geometrias são `[latitude, longitude]`. Para completar a cidade, usar
instância local/privada com perfil **pedestre**, nunca perfil de automóvel.
A API Table pode fornecer matriz de custos, mas não substitui as geometrias e a
verificação dos acessos exigidas aqui. Não enviar milhões de pedidos ao serviço público.

## Verificação e limites conhecidos

Testes em `transit.test_sptrans_graph`: sentidos, shapes curvos/ausentes, ocorrências
repetidas, calendários, virada de dia, frequências, seleção de viagem mais rápida,
conexões a pé dirigidas, 4,5 km/h, impossibilidade de embarcar antes da chegada,
contagem de baldeações, decomposição do custo, invalidação de cache/GTFS e limites.

O importador GTFS atual não preserva campos como `pickup_type`, `drop_off_type`,
`transfers.txt` ou `pathways.txt`. Este índice herda essa limitação, aplica a margem
uniforme existente e não alega implementar todas as restrições opcionais do GTFS.
O índice usa SQLite/B-tree: consultas indexadas não são formalmente O(1).
As etapas seguintes são completar as caminhadas, ampliar benchmarks comparáveis
e integrar a seleção por coordenadas e as previsões operacionais ao novo planejador.

Fontes primárias consultadas:

- [Referência GTFS](https://gtfs.org/documentation/schedule/reference/): stop_times, shapes, frequencies e calendários.
- [OSRM Route Service](https://project-osrm.org/docs/v5.24.0/api/#route-service): distância e geometria do percurso.
- [Condições do roteador público](https://routing.openstreetmap.de/about.html): limites do serviço compartilhado.

## Resultado local em 7 de outubro de 2026

Banco de aproximadamente 591 MiB: 22.061 paradas de ônibus, 2.239 padrões,
2.588.077 conexões diretas e 1.687.892 candidatos pedestres. Quatro percursos
reais foram verificados; 1.687.888 permanecem pendentes. Há 42 conexões com
distância de ônibus desconhecida e uma viagem com horários inválidos excluída
(`626A-10-1`). A exclusão não corresponde à remoção da linha inteira.

Passaram 173 testes de backend e o build do frontend. O SQLite passou pela
verificação de integridade. Medianas locais com cache aquecido: aproximadamente
0,5–2 ms para 0/1 baldeação e 40–106 ms para 2 baldeações nos exemplos medidos.
Não são um benchmark do fluxo completo da aplicação nem prova de ganho frente ao
planejador atual. As medições e contagens estão em
[validacao-busca-bidirecional.json](validacao-busca-bidirecional.json).
