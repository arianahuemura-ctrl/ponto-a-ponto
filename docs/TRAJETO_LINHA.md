# Trajeto completo ao acompanhar uma linha

Contrato aditivo de `GET /api/sptrans/trips/<trip_id>/?origin=<stop>&next=1&all=1` (também disponível para acompanhamento de veículo): manter os campos existentes e acrescentar `itinerary` com `geometry` (traçado GTFS completo), `before`, `after`, `terminal` (última parada da sequência), `boarding_index` e `split_available`.

A divisão usa a projeção ordenada das paradas sobre o traçado GTFS, independente das posições/previsões de veículos. Origem repetida sem índice explícito ou projeção indisponível não autoriza escolher uma ocorrência arbitrária: retornar traçado completo sem divisão e informar a limitação. Sem shape, não inventar caminho em linha reta.

No mapa de acompanhamento: antes do embarque em lilás tracejado, após o embarque em azul contínuo (variantes já usadas); último ponto com bandeira. O marcador é informativo e não preenche o destino da viagem. Veículos continuam sujeitos às regras existentes de disponibilidade e expiração. O itinerário estático permanece após indisponibilidade da atualização em tempo real.

Validação com dados artificiais: 18 testes de backend (divisão, projeção, paradas repetidas, ausência de veículos e regressões do acompanhamento), 11 testes unitários do frontend e 3 testes de navegador (linha sem veículos, linha com veículos e veículo individual). Os testes de navegador verificam permanência do traçado após falha de rede e que a bandeira não altera o destino do passageiro. Capturas em `frontend/test-results/line-itinerary-*.png`.

Correção de divergência no final: `terminal` preserva a última parada cadastrada; `endpoint` identifica a posição da bandeira e sua `kind` (`stop` ou `shape`). `terminal_mismatch` indica que a última parada não acompanha o final do shape (distância direta ou extensão restante superior a 150 m, ou projeção indisponível). Nesse caso, não inventar parada: marcar “Fim do traçado GTFS”, informar a divergência e preservar a geometria completa. O limiar é uma tolerância geométrica, não uma validação operacional do terminal.
