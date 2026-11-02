# Atendimento cadastrado da ARTESP em Mauá — 02/11/2026

A materialização combinada foi concluída. O recorte municipal identifica
**337 pontos da ARTESP, 16 linhas ou variantes e 705 viagens programadas por
dia útil** com embarque ou desembarque em Mauá. Os 337 pontos têm coordenadas
distintas, horários utilizáveis e destinos materializados como origem.

| Dia de serviço examinado | Pontos atendidos | Linhas/variantes | Viagens distintas |
| --- | ---: | ---: | ---: |
| Terça-feira, 03/11/2026 | 337 | 16 | 705 |
| Sábado, 07/11/2026 | 324 | 12 | 427 |
| Domingo, 08/11/2026 | 324 | 12 | 359 |

“Viagem” significa uma execução cadastrada de uma linha em um sentido, por
data de serviço GTFS. A mesma viagem foi contada uma única vez, mesmo passando
por vários pontos de Mauá. Não significa veículo distinto, passageiro atendido,
rota origem–destino materializada ou operação observada em campo. Os 1.491
registros de viagens distribuem-se entre os três calendários acima.

## Método e evidência

Foram cruzadas as coordenadas do GTFS ARTESP `20261007` com o polígono municipal
de Mauá (`3529401`) da
[malha municipal detalhada do IBGE de 2024](https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/malhas_municipais/municipio_2024/UFs/SP/SP_Municipios_2024.zip).
A seleção considera a posição geográfica, e não apenas o nome da linha ou o
endereço textual. A malha simplificada da API foi consultada inicialmente;
as contagens finais usam o arquivo detalhado. Cinco pontos incluídos ficam a
até 20 m da divisa; a lista de pontos próximos à divisa, inclusive os externos,
foi preservada para revisão da precisão cadastral.

Todas as 1.491 viagens selecionadas têm pelo menos dois pontos distintos,
horários válidos e sequência temporal não decrescente. As posições na sequência
foram verificadas para distinguir embarque de desembarque. Uma segunda consulta
SQL confirmou independentemente as contagens de viagens, linhas e pontos por
calendário. Os bancos de transporte foram acessados somente para leitura.

- [Resumo, metodologia, hashes e conferência SQL](../artifacts/benchmarks/maua-artesp-20261102/summary.json).
- [337 pontos e suas linhas](../artifacts/benchmarks/maua-artesp-20261102/stops.csv).
- [Linhas e viagens por calendário](../artifacts/benchmarks/maua-artesp-20261102/routes.csv).
- [Identificadores das viagens examinadas](../artifacts/benchmarks/maua-artesp-20261102/trips.csv).
- [Destinos materializados por origem de Mauá](../artifacts/benchmarks/maua-artesp-20261102/materialized-origins.csv).
- [Script do censo](../artifacts/benchmarks/maua-artesp-20261102/audit.py).

As linhas/variantes são: 040, 040EX1, 063, 063EX1, 064, 107, 157, 158,
158BI1, 160, 160EX1, 177, 336, 382, 382EX1 e 403. Seis delas não mencionam
Mauá no nome, embora tenham pontos cadastrados dentro do município.

## Variação temporal

Na terça-feira examinada, estas faixas do dia civil têm ao menos um embarque
cadastrado em Mauá. Uma mesma viagem pode aparecer em faixas diferentes; os
valores não devem ser somados para obter o total diário.

| Faixa | Viagens distintas com embarque local | Pontos com embarque | Linhas/variantes |
| --- | ---: | ---: | ---: |
| 00:00–04:00 | 22 | 194 | 10 |
| 07:00–09:00 | 103 | 337 | 16 |
| 12:00–14:00 | 81 | 337 | 15 |
| 17:00–19:00 | 92 | 337 | 16 |

Para essas faixas foram consideradas também as viagens de dias de serviço
anteriores cujos horários GTFS ultrapassam 24:00. A contagem exige apenas um
embarque no intervalo, não que a viagem inteira caiba nele.

## Transporte ferroviário e alcance da conclusão

O mesmo recorte identifica três estações já existentes na base ferroviária:
Capuava (`18934`), Mauá (`18935`) e Guapituba (`18937`). Elas são adicionais
aos 337 pontos ARTESP. As viagens ferroviárias são modeladas por frequências;
seus registros não foram somados às viagens de ônibus da tabela.

A validação da materialização já retornou uma alternativa ARTESP 158 → Metrô
L2 de um ponto em Mauá a Trianon-Masp, além da alternativa CPTM L10 → Metrô L2
saindo da estação Mauá, para 03/11/2026 às 08:00. Os detalhes estão no
[relatório da materialização](artesp-materialization.md).

O resultado comprova oferta programada utilizável na base combinada e
possibilidade de planejamento regional. Os horários intermediários ARTESP são
interpolados, o calendário cobre 2026 e não contém exceções de feriados.
Não se pode concluir disponibilidade operacional em tempo real. Não estão
incluídos todos os serviços municipais da Suzantur, nem foi medida cobertura
populacional. O percentual estrutural anterior de 99,666% refere-se a outro
universo de pares e não deve ser apresentado como percentual de Mauá atendido.

A base combinada foi ativada no servidor público em 02/11/2026, após autorização
do responsável. O catálogo respondeu com 47.379 pontos, incluindo 25.105 ARTESP,
e nova revisão de cache. A ativação não representa implantação física de QR Codes
ou validação presencial com passageiros.
