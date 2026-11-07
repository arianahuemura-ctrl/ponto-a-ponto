# Publicação concorrente de alternativas

O contrato HTTP SSE/NDJSON permanece: cada evento contém `journeys` e
`complete`; somente o último evento tem `complete=true`. Uma rota verificada
pode ser enviada enquanto outra fonte ainda está calculando. Limites de cinco
opções, custo ponderado e filtros permanecem aplicados a cada publicação.

Materialização, índice antigo, RAPTOR e caminhada direta trabalham em tarefas
independentes. Cada tarefa cria e fecha sua conexão SQLite na própria thread.
A caminhada externa deixa de anteceder obrigatoriamente a leitura materializada.
O consumidor WSGI não chama alternadamente os geradores lentos: consome uma fila
de resultados e emite eventos de progresso quando não há novidade.

Por processo servidor, há quatro workers exclusivos para materialização e oito
para buscas complementares, com limites de tarefas admitidas de 16 e 24.
Saturação, falha ou prazo de 30 segundos preservam resultados já obtidos e
indicam `search_limited`, com a fonte afetada. Não se declaram buscas ótimas
nesses casos. Encerrar o stream cancela tarefas ainda em fila; tarefas em
execução encerram cooperativamente na próxima publicação, respeitando também
os limites internos dos cálculos e das requisições pedestres.

A revisão opcional de embarque/desembarque continua na finalização do fluxo,
com seu orçamento próprio; não antecede a publicação das opções parciais.
Caminhadas curtas já materializadas mantêm o caminho local imediato.

Validação em 01/11/2026: 127 testes de backend e três de navegador aprovados.
O teste de concorrência mantém RAPTOR, índice antigo e caminhada bloqueados,
descarta a primeira alternativa materializada por trecho de ônibus curto e
confirma que a segunda alternativa chega antes de liberar as outras fontes.
No banco real, o par 840000672 → 940004126 entregou a linha 1732-10 em 0,423 s
com os complementos bloqueados e `complete=false`. Esse é um teste local,
não uma estimativa de latência de rede móvel.

Evidência: `artifacts/benchmarks/async-first-route-20261101.json`.
Os levantamentos anteriores de 3.264 consultas representam o fluxo sequencial
anterior à alteração e não devem ser apresentados como desempenho do novo fluxo.

O leitor classifica as sequências por horários sem construir seus traçados.
A geometria é preparada somente para a alternativa que será publicada,
evitando trabalho das outras opções antes da primeira resposta.

Após o reload final, o servidor respondeu HTTP 200 e enviou uma rota de
transporte por SSE com `complete=false`. No par 790015064 → 800016539, a
primeira resposta de transporte levou 6,22 s no horário real da consulta;
essa verificação não atribui a resposta a uma fonte específica nem demonstra
uma redução geral de latência. Evidência:
`artifacts/benchmarks/async-http-transport-20261101.json`.
