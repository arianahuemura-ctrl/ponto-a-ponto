# Contrato de baldeações ponderadas

`GET /api/sptrans/board/`, com e sem streaming, admite `max_transfers` inteiro
de 0 a 4 (padrão 4). O parâmetro é um teto de custo, não de trocas físicas.
O primeiro embarque custa zero. Cada troca envolvendo ônibus ou caminhada
externa custa 1; uma troca interna entre metrô e trem custa 1/3.
O cálculo usa inteiros em terços para evitar arredondamento nas fronteiras.

Cada viagem mantém `transfers` como número real de trocas e acrescenta
`transfer_cost_units` (terços), `transfer_cost` e `internal_rail_transfers`.
Espera, circulação interna, caminhada e tempo nos veículos não recebem desconto.
O embarque inicial por outra plataforma do mesmo complexo não é uma troca.

As alternativas publicadas têm custo até `min(max_transfers, mínimo + 1)`.
São mantidas até **cinco rotas de transporte por par**: primeiro as de custo
mínimo, e só as vagas restantes usam custos maiores dentro dessa faixa. Custos
menores têm precedência sobre velocidade; entre custos iguais, menor duração,
menor caminhada e identificador estável fazem o desempate. A ordenação
visual escolhida pelo passageiro atua depois da seleção das cinco.
O mínimo considera viagens de transporte verificadas para a consulta, incluindo
as alternativas materializadas. Caminhadas ainda não verificadas não podem
reduzir esse limite. Uma caminhada exclusiva não define o mínimo de transporte.
`transfer_policy.minimum_found` e `maximum_allowed` descrevem cada snapshot;
resultados parciais podem ser removidos quando aparece um mínimo menor.

Os limites de tempo e verificação continuam explícitos: mínimo encontrado não
significa mínimo global certificado se `search_limited` ou `walking_incomplete`.
A busca preserva estados de diferentes custos e últimas linhas para não perder
uma conexão econômica porque outra opção chega antes à estação intermediária.
O teto 4 permite até 12 trocas internas ferroviárias (13 embarques).

A materialização existente de ônibus permanece utilizável como fonte rápida.
Ela não demonstra cobertura de toda a cidade nem de quatro baldeações.
Não iniciar uma materialização exaustiva por inferência de espaço disponível.

## Capacidade medida em 01/11/2026

Disco livre: 244.922.974.208 bytes (228,10 GiB). Materializado atual:
117.727.232 bytes (112,27 MiB), 644.942 caminhos e cerca de 77.988 pares,
com `city_complete=false`. O esquema e o gerador aceitam somente 1 ou 2
embarques, exclusivamente de ônibus. A base fatorada tem 2,84 GiB.

A rede contém 22.274 pontos: 496.108.802 pares ordenados distintos. Isso é
o universo possível, não a quantidade de pares alcançáveis em um horário.
Medindo páginas SQLite, os caminhos atuais usam aproximadamente 162 bytes
por caminho com índices, e cada registro de cobertura usa 85 bytes.

| Caminhos por par | Cenário de armazenamento |
|---|---:|
| 1 | 114 GiB |
| 2 | 189 GiB |
| 4 | 339 GiB |
| 5 | 413 GiB |
| 8 | 638 GiB |

Esses cenários pressupõem todos os pares, um registro de cobertura por par
e o tamanho dos caminhos curtos atuais. Não são uma previsão do materializado
ponderado: menos pares alcançáveis reduzem o total, enquanto caminhos de até
13 embarques, alternativas adicionais, índices e arquivos temporários aumentam.
Portanto, não há evidência de que **todos os trajetos** até custo 4 caibam.
O corte mínimo + 1 reduz possibilidades, mas não limita quantas alternativas
distintas existem em cada faixa. Uma materialização seletiva ou sob demanda
é compatível com o espaço atual; uma expansão exaustiva precisa de amostragem
do novo formato antes de reservar o disco.

Medição reproduzível registrada em
`artifacts/benchmarks/materialization-capacity-20261101.json`.

## Retenção no materializado existente

A retenção de até cinco sequências distintas também se aplica ao gerador offline
de ônibus e à base ativa já produzida. O ranking estrutural prioriza o número
de baldeações e usa distância como desempate; a duração real de planejamento
é avaliada na consulta. A base antiga contém somente ônibus, portanto todas
as suas trocas custam 1. Não foram tratados metrô/trem como ônibus na nova busca.

O artefato foi preparado em cópia e validado antes da ativação. A retenção reduz
644.942 caminhos para 222.728 sequências em 77.956 pares não vazios: de 112,27
para 41,76 MiB. A cobertura municipal permanece incompleta. A API e seu cache
selecionam até cinco rotas verificadas com o custo ponderado e mínimo + 1.
