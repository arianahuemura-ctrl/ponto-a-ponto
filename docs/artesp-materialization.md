# Rede combinada SPTrans, trilhos e ARTESP

## Fontes e escopo

O GTFS ARTESP de versão `20261007` foi obtido no
[portal oficial](https://dadosabertos.artesp.sp.gov.br/dataset/gtfs).
O ZIP original e os relatórios de importação ficam em
`artifacts/transport/artesp-20261102/`. A pasta contém dados grandes e não entra
no Git. O catálogo combinado é `network.sqlite3`; o catálogo SPTrans original
e suas materializações permanecem preservados.

IDs ARTESP recebem o prefixo `artesp:` em paradas, linhas, viagens, calendários,
shapes e referências. Pontos das duas fontes não são fundidos por proximidade.
O arquivo original conserva os dados completos; agência, informação do feed e
tarifas também ficam em tabelas `source_artesp_*` no catálogo combinado.

Foram importados 25.105 pontos, 823 linhas, 86.724 viagens, 4.555.603 registros
de horários/paradas e 1.889.647 vértices de traçados da ARTESP. A rede combinada
tem 47.379 pontos e 2.188 linhas. Há 1.872 viagens cadastradas sem sequência de
paradas; elas são preservadas no catálogo, mas não produzem trechos utilizáveis.

Os horários intermediários ARTESP são interpolados, o calendário cobre 2026 e
não fornece exceções de feriados. Não foram importadas previsões ao vivo nem
a rede municipal completa da Suzantur. Cobertura estrutural não significa
viabilidade em todos os horários.

## Resultado da execução de 02/11/2026

Importação e geração concluídas com 32 processos. A etapa de custo um coube
na reserva de disco, portanto foi executada após a etapa zero. Os números
incluem as caminhadas diretas elegíveis e representam pares direcionados.

| Etapa | Pares cobertos | Alternativas | Banco de rotas |
| --- | ---: | ---: | ---: |
| Custo zero | 23.283.736 | 41.595.356 | 1,18 GiB |
| Até custo um | 338.126.510 | 1.277.212.025 | 33,28 GiB |

A segunda etapa amplia o mesmo arquivo; não há uma segunda cópia de custo
zero. Foram verificadas 1.680.832 ligações pedestres de até 1.000 m, incluindo
271.192 ligações direcionadas entre as fontes ARTESP e SPTrans/trilhos.
As 165.012 caminhadas diretas que tinham vaga na etapa zero foram preservadas
no limite de cinco alternativas. Todo o conjunto novo ocupa 36,14 GiB;
restaram 98,79 GiB livres, acima da reserva de 25 GiB.

A checagem integral do SQLite passou. Uma amostra de 32 origens, com 233.369
pares e 882.538 alternativas, coincidiu byte a byte com a geração sequencial.
Após preservar as vagas pedestres, outra amostra de 32 origens e todos os
165.012 pares reservados foram verificados. Os 42 testes de importação,
geração paralela e caminhadas passaram. O hash da base original e o tamanho
e a data de modificação de sua materialização permaneceram iguais.

Consultas pelo planejador local para **03/11/2026 às 08:00**, utilizando os
horários cadastrados, retornaram:

- Mauá, ponto `artesp:64476`, até Trianon-Masp: ARTESP 158 → Metrô L2,
  custo 1, duração programada de 145 minutos; primeira opção em 9,46 s,
  incluindo o carregamento inicial da fonte.
- Estação Mauá (`18935`) até Trianon-Masp (`18859`): CPTM L10 → Metrô L2,
  custo 1/3, duração programada de 68 minutos; primeira opção em 0,47 s.
- Pontos `artesp:48804` → `artesp:5776`: uma alternativa direta da ARTESP
  064, custo zero, duração programada de 130 minutos. A primeira resposta,
  em 0,35 s, também trouxe uma alternativa com transferência mais rápida.

Esses tempos são verificações funcionais locais, não um benchmark HTTP nem
confirmação da operação observada. As respostas completas e os scripts da
execução estão na pasta dos dados. O
[relatório consolidado](../artifacts/benchmarks/artesp-materialization-20261102.json)
registra fontes, contagens, validações e espaço. O tempo da etapa um nesse
relatório corresponde à última execução retomada, não ao tempo total.

## Caminhadas e custos

O extrato OSM local do Sudeste foi recortado ao redor dos pontos das duas redes,
preservando ruas completas e nós com barreiras. O recorte conserva uma margem
superior ao limite de caminhada. Foi usado OSRM 6.0.0 com perfil `foot`, 32
threads e 32 trabalhadores na matriz. O hash do recorte consta em `walks.json`.

Ligações pedestres precisam ter percurso confirmado de até 1.000 m, incluindo
o acesso à rede, com aproximação de cada ponto limitada a 20 m. Nenhuma reta
geográfica é publicada como percurso pedestre. Caminhadas diretas de até 300 m
ocupam uma das cinco vagas por par, quando havia vaga na etapa zero. Essa vaga
é preservada ao completar com rotas de custo um.

Cada par armazena no máximo cinco alternativas: custo mínimo primeiro, depois
as demais dentro do teto autorizado. Troca envolvendo ônibus ou caminhada
externa entre veículos custa 1; troca interna ferroviária custa 1/3. Custo até
1 admite uma troca de ônibus ou até três trocas internas ferroviárias.
Horários são reavaliados quando a viagem é consultada.

## Reprodução

Importação em uma saída nova, sem substituir a base ativa:

```sh
.venv/bin/python backend/manage.py import_artesp \
  --archive artifacts/transport/artesp-20261102/artesp_gtfs.zip \
  --base sptrans.sqlite3 \
  --database /caminho/novo/network.sqlite3 \
  --report /caminho/novo/import.json
```

Prepare o grafo com `staged_materialized.walking_graph`, o recorte com
`scripts/crop_combined_foot.py` e a matriz com `walk_artifacts.build`, usando
um roteador OSRM local. A variável `SPTRANS_DATABASE` deve apontar para o
catálogo combinado em todas as etapas. Arquivos de caminhadas de outra fonte
são rejeitados por assinatura.

Depois da matriz pedestre verificada:

```sh
SPTRANS_DATABASE=/caminho/novo/network.sqlite3 \
.venv/bin/python backend/manage.py materialize_sptrans_staged \
  --walks /caminho/novo/network.staged-walks.sqlite3 \
  --stages 0 --workers 32 --short-walks --min-free-gib 25
```

Meça o espaço antes da etapa seguinte:

```sh
SPTRANS_DATABASE=/caminho/novo/network.sqlite3 \
.venv/bin/python backend/manage.py materialize_sptrans_staged \
  --stages 1 --workers 32 --short-walks --min-free-gib 25
```

Os 32 processos têm motores nativos isolados e compartilham as estruturas
imutáveis por `fork`. Somente o coordenador grava no SQLite. A fila é limitada
e as transações publicam caminhos e checkpoints juntos. A geração pode ser
retomada sem anunciar como completa uma etapa parcial. A assinatura preserva
o mesmo formato do gerador sequencial.

A reserva pedestre é reconstruível a partir da etapa zero e tem checkpoint
por origem. Ao reservar uma caminhada, somente a quinta alternativa de
transporte é retirada, quando necessário, mantendo as quatro prioritárias.
Pares que já tinham cinco serviços diretos na etapa zero ficam intactos.

## Publicação

Gerar estes arquivos não muda automaticamente a configuração do servidor.
`SPTRANS_DATABASE` seleciona o catálogo; seus artefatos derivados usam o mesmo
prefixo. A ativação deve considerar também os leitores legados, a identificação
da fonte nos serviços de previsão e o endpoint usado para geometria pedestre.
Não redirecionar previsões ARTESP para a API de veículos da SPTrans por simples
coincidência no número da linha.

### Ativação concluída em 02/11/2026

Antes da ativação, o servidor publicava 22.274 pontos, sem ARTESP. A
configuração ativa aponta `SPTRANS_DATABASE` para o catálogo combinado e
`SPTRANS_LEGACY_DATABASE` para `sptrans.sqlite3`. O leitor suplementar consulta
as materializações antigas em paralelo, com contexto isolado por trabalhador,
preservando alternativas de custos superiores a um. Não são copiados nem
reescritos os bancos existentes.

As consultas de previsão e posição rejeitam identificadores `artesp:` antes
de acessar a SPTrans. Na listagem de linhas ARTESP, as próximas partidas são
reunidas entre todas as viagens ativas da linha e sentido. O catálogo do mapa
recebe outra revisão/ETag, permitindo substituir o cache após recarregar a
página.

A pré-validação confirmou 47.379 pontos, sendo 25.105 ARTESP e todos os 337
do recorte municipal de Mauá. Também retornou ARTESP 158 → Metrô L2 e preservou
uma alternativa anterior de custo 3. Passaram 60 testes específicos. Uma
execução mais ampla encontrou três testes antigos incompatíveis com o fluxo
concorrente; os três também falharam com as alterações desta ativação removidas
do módulo de composição em memória. Eles não foram alterados neste trabalho.

Registro: [validação da ativação](../artifacts/benchmarks/artesp-activation-20261102.json).
Após autorização explícita do responsável, a configuração foi aplicada e o
servidor recarregado. A consulta HTTP confirmou 47.379 pontos, incluindo 25.105
ARTESP, com novo ETag `stops-v1-aa630c9a43500b095583c385`. A versão anterior
da configuração foi preservada para reversão.
