# Dados e cenários do MBM

O arquivo backend/transit/data/demo.json define o recorte reproduzível da
demonstração. As coordenadas e os identificadores foram extraídos do levantamento
OSM de Mauá de 23/09/2026 (levantamento_osm_maua/dados_osm.json, no projeto PI2).
A data da base está registrada em source_timestamp.

Dados geográficos © colaboradores do OpenStreetMap, sob
[ODbL](https://www.openstreetmap.org/copyright). Cada parada mantém seu link OSM.
O terminal usa o centro do objeto way, que não representa uma plataforma
precisa. Os demais objetos selecionados são nós de parada.

## Complementações fictícias

A consulta original não basta para reconstruir a rede municipal. Não foram
atribuídos códigos de linhas reais às conexões inventadas. Todas as linhas usam
o prefixo **DEMO**. Nomes com “(demo)” são rótulos de apresentação, não nomes
oficiais nem evidência de uma escola ou trabalho naquele endereço.

São simulados: associação entre paradas e linhas, sentido, sequência, horários,
durações, conexões e posições dos veículos. Os percursos no mapa acompanham ruas obtidas do OSM via OSRM, perfil driving.
São hipóteses de deslocamento para demonstração, não itinerários oficiais validados.
Nenhuma complementação foi enviada ao OSM.

| Linha | Sequência demonstrável | Minutos entre paradas |
|---|---|---|
| DEMO-A | Terminal → Norte → Escola | 8, 18 |
| DEMO-B | Terminal → Oeste → Conexão Central | 4, 4 |
| DEMO-C | Conexão Central → Escola → Trabalho | 5, 5 |
| DEMO-D | Terminal → Sul → Trabalho | 12, 20 |
| DEMO-E | Terminal → Escola, expresso | 12 |
| DEMO-R | Trabalho → Escola → Terminal | 6, 13 |

Uma oitava parada foi mantida sem ligação para testar ausência de conexão.
O sentido inverso não é inferido; precisa de uma viagem cadastrada.

Partidas são geradas entre 06:00 e 22:00, com intervalos de 15 minutos
(30 minutos no expresso) e deslocamentos iniciais definidos no JSON. Cada
viagem recebe um identificador estável. O mesmo horário reproduz os mesmos
veículos e previsões. Não existe atualização por GPS real.

## Dijkstra

O servidor representa eventos de chegada por viagem, parada e número de
embarques. As arestas permitem continuar no veículo ou embarcar em qualquer
partida viável. Os pesos correspondem a espera + deslocamento e são não
negativos. Trocas exigem pelo menos 120 segundos. Permanecer no mesmo veículo
não impõe esse intervalo.

Todas as viagens na janela são examinadas, inclusive ônibus posteriores da
mesma linha. Para comparar opções, executa-se a busca condicionada à primeira
linha de embarque e exibem-se até cinco alternativas, ordenadas pela chegada.
O menor tempo é garantido dentro da rede e horários simulados e do limite
de trocas escolhido (0 a 4), não para toda a rede real de Mauá.

Para destinos livres no mapa ou por endereço, são consideradas todas as
paradas a até 500 m. Soma-se uma caminhada a 1,3 m/s, calculada em linha reta.
Ainda não há roteamento por calçadas, acessibilidade ou validação de travessias.
Os favoritos guardam a localização e podem reutilizar a parada selecionada.

## Roteiro de demonstração

Todos os cenários abaixo partem às 08:00.

1. **Viagem direta:** Terminal → Norte. DEMO-A sai às 08:02 e chega às 08:10.
2. **Baldeação mais rápida:** Terminal → Trabalho. DEMO-B sai às 08:04 e chega
   à Conexão Central às 08:12. DEMO-C sai às 08:15 e chega às 08:25.
   Total: 25 min; espera: 7 min; deslocamento: 18 min; uma troca.
   Limitando a viagens diretas, DEMO-D chega às 08:33.
3. **Expresso que sai depois:** Terminal → Escola, sem trocas. DEMO-E sai às
   08:10 e chega às 08:22, antes da DEMO-A que sai às 08:02 e chega às 08:28.
   Com trocas permitidas, a conexão B + C chega às 08:20.
4. **Sem conexão:** Terminal → Parada sem conexão. A interface explica que
   não há trajeto disponível, sem inventar uma linha.
5. **Favoritos:** salve Trabalho com o nome Casa, recarregue a página e use
   “Voltar para casa”. Remova o favorito após a apresentação, se desejado.
6. **Acompanhamento:** selecione uma alternativa e “Acompanhar esta viagem”.
   Inicie o relógio em /admin/. A viagem escolhida é preservada enquanto os veículos
   avançam; Volte à lista de alternativas para recalcular a partir do horário corrente.

Veículos são interpolados por distância ao longo da geometria viária de cada trecho.
Até 15 minutos antes da partida, são mostrados na origem como aguardando saída.
Ao selecionar uma parada, o mapa destaca os próximos veículos de suas linhas;
ao selecionar uma viagem, mostra os veículos que a compõem. O quadro apresenta
até três próximas partidas por linha, dentro de uma hora simulada.

## Avaliação com a comunidade

A interface oferece perguntas baseadas no relatório e um campo de observações.
Registros ficam em SQLite no servidor e podem ser exportados pelo comando
python backend/manage.py export_evaluations. Não há lista pública de respostas.
A validação com Osmar não foi realizada automaticamente: deve ocorrer em uma
apresentação real. Testes automatizados usam banco temporário próprio.

## Geometrias viárias e configuração atual

O arquivo route_geometry.json mantém coordenadas, nomes de ruas, distância,
pontos ajustados à via e data da consulta. Ele foi obtido com o serviço Route do
[OSRM](https://project-osrm.org/docs/v5.24.0/api/). O comando refresh_route_geometry
permite reconstruí-lo. Seus tempos não substituem os tempos mockados do cenário.

Os códigos visuais são: DEMO-A → 101, DEMO-B → 210, DEMO-C → 307,
DEMO-D → 405, DEMO-E → 511, DEMO-R → 703. Prefixos DEMO permanecem nos IDs internos.

O relógio e a ativação agora pertencem à administração Django. Para reproduzir
os cenários descritos, configure 08:00:00 e desmarque Relógio em movimento.
As páginas públicas usam o horário global do servidor e não aceitam sobrescrevê-lo
por parâmetros. Não há botões de cenários na interface principal.
