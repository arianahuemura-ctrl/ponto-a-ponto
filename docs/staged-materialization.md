# Materialização municipal em etapas

## Caminhadas diretas de até 300 m

`short_walk_paths` armazena uma opção exclusivamente pedestre por par com vaga,
sem modificar as três tabelas de transporte. O limite é de 300 m do percurso
verificado pelo OSRM foot, incluindo os acessos à rede, e não da distância em
linha reta. Somente registros `verified` entram. Pares que já têm cinco rotas
ficam intactos; a caminhada ocupa uma vaga nos demais, incluindo pares vazios.

Execute `.venv/bin/python backend/manage.py materialize_sptrans_short_walks`.
A publicação é atômica e retomadas concluídas são idempotentes. A assinatura
confere a base de transporte e o arquivo pedestre. O leitor exige correspondência
de IDs e coordenadas: um endereço ou GPS deslocado não herda uma caminhada salva.
Tempo e distância são recuperados sem chamada ao roteador. O traçado é carregado
sob demanda quando a caminhada é selecionada, respeitando o controle de acesso
do roteador público já existente; nenhum traçado reto substitui uma geometria
pedestre ausente. A lista de opções mantém no máximo cinco, incluindo caminhada.

### Resultado em 01/11/2026

Foram acrescentadas 1.337 caminhadas verificadas, preenchendo 255 pares antes
vazios e completando 241 pares até cinco opções. Restam 1.657.654 pares sem
materialização. Os 115.741 candidatos cujos pares já tinham cinco rotas foram
preservados. O acréscimo no banco foi de 286.720 bytes (280 KiB).

Todas as 1.337 entradas foram comparadas com a fonte pedestre e as contagens
de transporte; a integridade da nova tabela passou. Os 50 testes de backend,
os dois cenários de caminhada no navegador e os dois de regressão do painel
passaram. O servidor foi recarregado e respondeu HTTP 200: a primeira resposta
local para 460008313 → 4614906 veio em cerca de 3,7 ms, com caminhada
materializada de 13,2727 m e 10,6181 s, sem geometria remota nessa etapa.
Essa medição local não representa a latência de rede do acesso público.

Evidências: `artifacts/benchmarks/short-walks-20261101.json` e
`artifacts/benchmarks/short-walks-validation-20261101.json`.

## Complementação autorizada até custo 4

O pedido seguinte amplia o teto para 12 terços (4 inclusive), somente nos pares
com menos de cinco rotas após a etapa menor que 3. Pares vazios também entram;
permanecem o teto de cinco, mínimo + 1 e o custo de ⅓ para trocas internas
ferroviárias. As duas tabelas anteriores ficam intactas; `topup_paths` armazena
somente pares que recebem novas sequências, mantendo o conteúdo anterior como
prefixo. `topup_progress` registra cada origem atomicamente. A consulta tenta
esse complemento antes de `expanded_paths` e `paths`. Cobertura até 12 terços
só é anunciada depois de todas as origens concluírem.

Execute `.venv/bin/python backend/manage.py materialize_sptrans_topup --max-cost 4
--workers 16`. A reserva mínima continua em 20 GiB. O novo gerador aceita até
13 embarques; preserva famílias exatas de prefixos para as exclusões de ônibus
que ainda cabem no orçamento. Uma busca reversa ignora exclusões de serviços
para obter um limite otimista: descarta somente estados incapazes de alcançar
qualquer destino com vaga dentro do respectivo custo permitido.
A busca avança por tetos de 9, 10, 11 e 12 terços em cada origem. Os resultados
de cada faixa alimentam a próxima, excluindo imediatamente os pares cheios;
somente o resultado final da origem é gravado.
Os limites otimistas são aplicados antes das caminhadas de transferência e dos
embarques, além da chegada. As exclusões de ônibus usam vetores de tamanho
limitado: no máximo cinco serviços de ônibus cabem em um caminho de custo 4.
As duas versões anteriores equivalentes deste gerador podem ser retomadas;
qualquer outra mudança de assinatura é rejeitada. Comparações byte a byte de
cinco origens reais e testes contra enumeração exaustiva estão registrados em
`artifacts/benchmarks/topup-pruning-validation-20261101.json` e
`artifacts/benchmarks/topup-smallsets-validation-20261101.json`.

Novo pedido: custo máximo estritamente menor que 3, portanto até 8 terços
(2⅔). Continuam valendo cinco sequências por par, preferência pelo custo mínimo
e complemento somente até mínimo + 1. O formato compacto admite até nove
embarques, sem alterar os identificadores dos trechos existentes. A ampliação
tem assinatura própria do gerador e checkpoint separado; as etapas 0 e 1
continuam disponíveis. A reserva de disco permanece em 20 GiB.

Refinamento confirmado: pares com cinco rotas não são alterados. A expansão
grava apenas complementos em `expanded_paths`, preservando byte a byte a tabela
`paths` anterior e as rotas originais de cada par. Pares vazios também podem ser
preenchidos. `expanded_progress` permite retomada por origem. Execute
`.venv/bin/python backend/manage.py materialize_sptrans_expanded --below-cost 3
--workers 8`. Os workers são processos isolados; não compartilham o motor nativo
nem conexões SQLite. Apenas o processo principal grava, com uma fila limitada.

O gerador mantém exatamente as exclusões de linhas ferroviárias já usadas.
Para ônibus, o orçamento restante permite excluir no máximo dois serviços
futuros: um primeiro ônibus retém cinco mais esse número de alternativas; com
uma exclusão restante, retém as cinco melhores e as cinco melhores que evitam
cada serviço presente nas primeiras cinco. Isso preserva as cinco melhores
continuações válidas, sem enumerar todas as permutações de ônibus. Redes pequenas
são comparadas com enumeração exaustiva, inclusive exclusões de dois serviços.

Pedido de 01/11/2026: concluir custo zero, medir disco; concluir custo até um,
medir novamente; não avançar para custos maiores sem nova decisão.

O artefato `sptrans.staged.sqlite3` é separado dos índices antigos. Mantém até
cinco sequências distintas por par dirigido, priorizando o custo em terços e
depois uma estimativa estrutural de duração. O horário efetivo é reavaliado na
consulta; não se materializam previsões ao vivo nem se afirma viabilidade em
todos os horários. Custo 1 abrange uma troca envolvendo ônibus ou até três
trocas internas ferroviárias. Caminhadas externas entre veículos custam 1.

Nas etapas 0 e 1, a geração é por origem, sem truncar os trechos intermediários
aos cinco resultados finais. Cada origem concluída é confirmada atomicamente; interrupções permitem
retomada. Uma etapa só fica completa após todas as origens, inclusive as que
não produzem caminhos, estarem confirmadas. Reserva mínima de 20 GiB: parar
preservando o progresso se ela for atingida. Não marcar cobertura incompleta
como completa. A rede pedestre é calculada localmente, incluindo estações.

A representação guarda referências a trechos e caminhadas, sem duplicar a
geometria de todas as rotas em cada par. As fontes e parâmetros são registrados
para invalidar resultados se mudarem. O servidor pode usar origens já prontas
durante a geração, mantendo o planejador dinâmico como complemento.

Execute `.venv/bin/python backend/manage.py materialize_sptrans_staged --walks
sptrans.staged-walks.sqlite3` após preparar a base pedestre local. Sem `--walks`,
o comando retoma a fonte já preparada. `--stages 0` permite concluir somente a
primeira etapa; o padrão é `--stages 0 1`. Relatórios ficam em
`artifacts/benchmarks/staged-cost-<etapa>-<data>.json`.
A geração das etapas 0 e 1 é sequencial. O experimento com motores em threads foi
desativado após um encerramento nativo inesperado; a retomada sequencial
concluiu as origens restantes. A causa do encerramento paralelo não foi confirmada.

A seleção de candidatos pedestres cobre todo o raio de 1 km, inclusive nas
bordas da grade espacial. A distância em linha reta apenas seleciona candidatos;
a inclusão depende do percurso confirmado pelo OSRM foot local. A assinatura
registra também o código do enumerador para impedir retomada com regras mistas.

## Resultado inicial das etapas 0 e 1 em 01/11/2026

Ambas as etapas cobriram as 22.274 origens. Custo zero: 24.195.933 rotas em
13.540.228 pares, banco de 683.163.648 bytes. Custo até um: 684.725.998 rotas
em 174.727.157 pares, banco acumulado de 18.968.801.280 bytes (17,67 GiB).
A base pedestre separada ocupa 475.631.616 bytes. Restaram aproximadamente
209,37 GiB livres após a validação; nenhuma etapa acima de um foi iniciada.

As verificações de integridade passaram. Todos os pares com ligação direta
continuam presentes, e todos os registros respeitam o limite de uma a cinco
rotas. A reprodução sequencial de 477 origens coincidiu integralmente com os
dados gravados; 6.787 rotas tiveram continuidade e custos conferidos em detalhe.
Evidências em `artifacts/benchmarks/staged-validation-20261101.json`.

## Complementação com custo menor que 3 em 01/11/2026

As 22.274 origens foram concluídas. Foram adicionadas 1.541.006.976 rotas,
incluindo 276.986.092 pares novos. O resultado lógico, sem contar duas vezes
os registros da base preservados no complemento, é de 2.225.732.974 rotas
em 451.713.249 pares. Foram atualizados 342.410.903 pares; aqueles que já
tinham cinco rotas permaneceram intactos.

O teto é de oito terços (2⅔), mantendo o custo mínimo + 1 e até cinco rotas
por par. Trocas internas ferroviárias custam um terço; as demais custam um.
O banco passou a ocupar 82.237.661.184 bytes (76,59 GiB), um acréscimo de
58,92 GiB em relação à etapa até um. Restaram aproximadamente 150,45 GiB
livres na medição após a geração.

A reprodução sequencial de 47 origens coincidiu byte a byte com os dados
gravados. Foram conferidos 725.463 pares atualizados, incluindo a preservação
dos prefixos anteriores, e 6.881 rotas tiveram continuidade, caminhadas e
custos verificados em detalhe. Evidências em
`artifacts/benchmarks/expanded-validation-20261101.json`.
O aplicativo já consulta os complementos e informa cobertura até oito terços.
A verificação integral `PRAGMA quick_check` terminou com resultado `ok`.
O relatório de conclusão está em
`artifacts/benchmarks/expanded-below-3-20261101.json`; seu tempo de geração
corresponde à última execução retomada, sem incluir a checagem de integridade.

## Resultado da complementação até custo 4 em 01/11/2026

As 22.274 origens foram concluídas. A etapa acrescentou 246.364.897 rotas e
42.737.644 pares novos, atualizando 55.935.169 pares que tinham vagas. O total
lógico passou a 2.472.097.871 rotas em 494.450.893 pares dirigidos, mantendo
intactas as tabelas anteriores e os pares que já tinham cinco rotas.

Agora há 494.391.013 pares com cinco rotas e 59.880 com uma a quatro rotas.
Dos 496.108.802 pares dirigidos entre paradas distintas, 1.657.909 continuam
sem rota materializada dentro dos critérios atuais. O banco ocupa
94.960.996.352 bytes (88,44 GiB), acréscimo de 11,85 GiB. Restaram cerca de
138,59 GiB livres após a geração.

A auditoria reproduziu 38 origens byte a byte, verificou 106.434 pares
atualizados e conferiu continuidade, exclusões de serviços, caminhadas e
custos de 7.596 rotas. A amostra inclui custos de 9, 10, 11 e 12 terços.
Evidências em `artifacts/benchmarks/topup-validation-20261101.json`.
Os 53 testes de regressão passaram. A consulta pública anunciou cobertura
até 12 terços; o leitor serviu uma nova rota com quatro embarques e custo 3
em aproximadamente 0,48 s, conforme
`artifacts/benchmarks/topup-reader-20261101.json`.

A recuperação indexada de 250 pares aleatórios, consultando até as três tabelas
em ordem de prioridade, teve mediana de 0,30 ms e percentil 95 de 0,51 ms.
Essa medição exclui geração de rotas e avaliação de horários, e foi feita
durante a checagem integral do banco. Evidências em
`artifacts/benchmarks/topup-pair-lookup-20261101.json`.

A verificação integral `PRAGMA quick_check` terminou com resultado `ok`.
O comando concluiu com código zero e registrou
`artifacts/benchmarks/topup-through-4-20261101.json`. O tempo nesse relatório
corresponde à última execução retomada e não inclui a checagem de integridade.
