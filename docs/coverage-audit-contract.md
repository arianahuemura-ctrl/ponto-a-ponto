# Contrato do levantamento de cobertura e primeira rota

Escopo autorizado: censo de todos os pares distintos, auditoria individual dos
59 pontos com acesso bloqueado e tempos por amostragem adaptativa com 32
processos. Não altera rotas, materializações nem limites do aplicativo.

Datas de referência: 03/11/2026, America/Sao_Paulo, 02:00 (madrugada), 08:00
(pico), 14:00 (entrepico). São cenários de programação, sem trânsito em tempo
real. Uma rota só conta quando o fluxo entrega uma lista não vazia após seus
filtros, e não ao responder um evento vazio ou terminar uma busca.

Cada grupo reúne pares por cobertura, modos/custo da materialização e distância,
separado por horário. Um lote tem 32 consultas distintas. Após o lote,
P90-P10 <= max(50 ms, 20% da mediana) caracteriza pouca dispersão quando todos
os resultados têm o mesmo estado. Só classificamos sucesso até 30 s quando
há primeira rota dentro do limite. Grupos variáveis recebem até quatro lotes de 32 consultas (128 no total);
se continuarem variáveis, ficam explicitamente inconclusivos/heterogêneos.
O critério de parada usa cada lote; o relatório preserva todos os resultados.

A medição local executa o gerador de produção com cache de resposta vazio e
rede GTFS carregada, incluindo avaliação de horários, geometria, filtros e
fallbacks. Exclui HTTP, túnel, navegador e tempo de fila de produção. Concorrência
32 é um cenário de carga local, não uma promessa de latência no celular.

Não se faz teste de carga no serviço público pedestre. Ao precisar de uma
chamada externa não armazenada, o teste registra `external_required`, com o
tempo até essa dependência, sem fingir que mediu o tempo até uma rota. Em
paralelo, registra o leitor materializado isolado para identificar se uma rota
local já poderia ser servida. Nenhuma geometria artificial é fornecida.

Os 30 s são um corte do experimento; timeouts não provam inexistência de rota.
Ausência no horário, dependência externa e inacessibilidade no modelo são
categorias distintas. Tempos amostrais não são atribuídos como medidos aos
496 milhões de pares.
