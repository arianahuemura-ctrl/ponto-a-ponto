# Rotas com ônibus, metrô e trens

Contrato implementado em 2026-11-01: `/api/sptrans/board/` mantém os snapshots
progressivos e acrescenta `mode` (`bus`, `metro`, `rail`), `route_type` e
`timing_detail` a cada trecho. `complete=false` enquanto houver alternativas em
avaliação. Horários ferroviários são estimativas programadas, sem posições de
trens inventadas. Os artefatos existentes de ônibus continuam somente leitura.

O planejador por rodadas compara conexões multimodais com as alternativas de
ônibus materializadas. Uma viagem mais rápida não é eliminada apenas por ter mais
baldeações. Caminhadas externas continuam exigindo roteamento verificado;
transferências internas usam uma lista explícita de complexos de estações.
Tempos internos são estimativas de planejamento, não percursos medidos.

As cores ferroviárias do GTFS são preservadas nos traçados, setas, círculos de
estações e identificadores da interface, tanto no tema claro quanto no escuro.
O trecho anterior ao embarque fica pontilhado, mantendo a cor da linha. A legenda
nomeia cada linha (por exemplo, Linha 1 · Azul), conforme o
[mapa da rede do Metrô](https://www.metro.sp.gov.br/sua-viagem/mapa-da-rede/).
Uma sessão antiga sem `color` usa a correspondência entre o código ferroviário
e a cor cadastrada; códigos desconhecidos recebem cinza neutro.

O traçado ferroviário usa um padrão de traço e ponto distinto do ônibus e da
caminhada. Estações têm símbolo quadrado com trem, sem setas de sentido no ponto;
as setas do itinerário continuam indicando o sentido da viagem selecionada.
Estações intermediárias usam quadrados, enquanto paradas de ônibus usam círculos.
As conexões internas, como Consolação (Verde) ↔ Paulista (Amarela), entram já no
primeiro resultado entre estações selecionadas, preservando o tempo de circulação
interna em `walks`. A interface informa a linha de chegada, a linha seguinte e
o sentido do próximo embarque. O contrato da API permanece compatível.

A ordenação continua pelo tempo total estimado: acesso, espera, circulação e
baldeações. Uma viagem longa não recebe um desconto artificial de tempo por usar
trens; alternativas ferroviárias e ônibus diretos permanecem comparáveis.

## Fontes e interpretação

- Marcelo Augusto Marques dos Santos, Metrô de São Paulo, ANTP (2013),
  [A importância dos tempos de parada na regulação de sistemas de metrô](https://files-server.antp.org.br/_5dotSystem/download/dcmDocument/2013/10/07/EC169CBF-5E55-4AA7-BCB2-8346961C32B7.pdf).
  A parada inclui portas abertas, aviso de fechamento e reação dos equipamentos.
  Os 10–30 s citados são de portas abertas, não a parada total. Não constituem
  uma tabela atual por estação. Adotamos 30 s totais como hipótese configurada de
  planejamento quando a separação não existe no GTFS, não como valor medido.
- Carlos Alberto de Sousa, [ACTREM, tese USP, defendida em 2015 e publicada no repositório em 2016](https://teses.usp.br/teses/disponiveis/3/3143/tde-22062016-084353/pt-br.html):
  estudo de controle de partidas/paradas e frenagem regenerativa com simulações
  da Linha 4-Amarela. Fundamenta separar circulação, parada e intervalo, mas não
  fornece uma previsão operacional atual para todas as linhas.
- [CPTM, apresentação técnica de manutenção de TUEs](https://www.cptm.sp.gov.br/licitacoes/Documents/Audiencias_Publicas/Apresentacao_Manutencao_de_TUEs_2016_retomada.pdf):
  referência de aceleração de 0,90 m/s²; especificações de frota não equivalem à
  aceleração média observada em todas as viagens.
- [Renovação da frota CPTM, revista Engenharia 613](https://brasilengenharia.com/portal/images/stories/revistas/edicao613/art_renovacao_613.pdf):
  referência de frenagem de serviço de 1,1 m/s².
- [Esclarecimentos técnicos para 44 trens do Metrô, 2022](https://www.stm.sp.gov.br/wp-content/uploads/2022/03/ATA_ESCL_Audiencia_44_Trens_assinada.pdf):
  frenagem de serviço de 1,2 m/s². Não usamos frenagem de emergência no planejamento.
- [Guia do passageiro, Metrô, outubro de 2026](https://www.metro.sp.gov.br/wp-content/uploads/2026/10/guia_do_passageiro_online.html)
  e [horários oficiais](https://www.metro.sp.gov.br/sua-viagem/horarios/): abertura,
  encerramento e limite para transferência. A Linha 17 tem operação transitória
  de segunda a sábado, 06h–22h. Para ela usamos intervalo conservador de 9 min,
  tomando como referência a [publicação sobre a operação ampliada](https://www.metro.sp.gov.br/2026/10/01/linha-17-ouro-transporta-mais-de-25-mil-passageiros-no-primeiro-dia-com-horario-ampliado/).
- [CPTM: transferências e intervalos](https://www.cptm.sp.gov.br/cptm/sua-viagem/transferencias-e-intervalos)
  e GTFS SPTrans importado: intervalos e calendário por serviço/faixa horária.

## Modelo

Espera com fase desconhecida: metade do intervalo ativo, supondo frequência
regular e chegada aleatória do passageiro. Partidas com horário exato usam a
próxima partida alcançável. A espera é calculada após o acesso representado no
modelo; veja abaixo os limites dos dados de entrada/saída das estações.
Aceleração/frenagem constantes dão `v_pico=min(v_limite,sqrt(2d/(1/a+1/b)))`;
`T_mov=v_pico/a + d_cruzeiro/v_pico + v_pico/b`. A curva é triangular quando não
há distância para cruzeiro. Distâncias vêm do traçado ferroviário GTFS, nunca de
uma reta apresentada como percurso real.

Hipóteses de plausibilidade: aceleração 1,0 m/s² no metrô e 0,9 nos trens;
frenagem 1,2 e 1,1 m/s²; limites de referência 80 e 90 km/h. Não são medições
por frota, nem limites de cada sinal/via. Curvas, rampas, restrições, lotação e
regulação não são simuladas. A programação GTFS prevalece quando é mais lenta.
Se chegada e partida são iguais, uma parcela da duração existente é reservada
à parada: não se acrescentam automaticamente 30 s a cada intervalo já agregado.
O modelo físico só eleva um tempo programado inferior ao mínimo de referência.
Dados ausentes preservam o tempo GTFS e informam a ausência da decomposição.
Algumas linhas têm tempos uniformes entre estações no GTFS. Eles continuam sendo
a referência, sem alegação de calibração empírica: o modelo físico estabelece
um piso de plausibilidade, não substitui medições de viagem por linha e horário.

A espera na plataforma é separada da caminhada e do tempo interno de transferência.
Não há garantia de conexão, precisão ao segundo, tarifa integrada ou lotação.

## Limites de cobertura e validação

### Rede visível no mapa

`GET /api/sptrans/rail-network/` retorna `{revision, lines}` sem exigir origem,
destino ou rota. Cada linha contém `route_id`, `code`, `name`, `mode`, `color`
e `geometries` (listas de coordenadas `[latitude, longitude]` do GTFS).
Inclui apenas metrô/trem com traçado disponível; viagens que compartilham o
mesmo traçado não o duplicam. O cache acompanha a revisão do GTFS.
A rede inteira permanece tracejada, sem capturar cliques, com cores opacas
e acima apenas dos azulejos do mapa. O trecho escolhido da viagem é sólido e
opaco, na cor da linha. Pontos e estações permanecem acima dos traçados.

O GTFS local contém 9 registros de rotas de metrô/monotrilho e 7 de trens
(inclui ramais, não significa 16 linhas independentes). A cobertura acompanha
esse arquivo. Concessionárias continuam com os códigos presentes no GTFS.
A seleção de acessos inclui estações em um raio de 1 km, com caminhada externa
verificada. O acesso termina na coordenada GTFS: escadas, bloqueios e tempo de
entrada/saída da plataforma ainda não têm um cadastro por estação. Transferências
internas cadastradas usam 2 min de circulação mais 2 min de margem de conexão.
O fechamento à meia-noite é conservador: não promete últimas partidas ou conexões
depois desse horário. A Linha 17 usa a janela transitória publicada; outras linhas
usam a frequência e o calendário do GTFS, limitados à janela de funcionamento.

A busca entrega resultados progressivos, mas tem limite de validação de caminhadas;
`search_limited` e `walking_incomplete` indicam quando a comparação é parcial.
Não se declara ótimo global nessas situações. O ônibus continua usando tempos
programados, sem um perfil histórico de congestionamento disponível neste banco.
