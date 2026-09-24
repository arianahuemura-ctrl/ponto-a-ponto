MAPA DE ÔNIBUS DE MAUÁ — PROTÓTIPO

1. O frontend está em `frontend/index.html`.
2. Para evitar bloqueios de requisições do navegador, execute na raiz do projeto:

   python backend/server.py

   O navegador será aberto automaticamente na URL disponível, normalmente `http://127.0.0.1:8000`.

   Se a porta 8000 já estiver ocupada, o servidor tentará automaticamente as próximas portas até 8009.

3. Informe um endereço em Mauá e clique em “Buscar”, ou clique em “Usar minha localização e buscar pontos”.
4. Clique em um ponto azul.
5. As linhas que passam por ele são desenhadas, e os pontos posteriores possíveis ficam verdes.
6. Clique em um segundo ponto verde. Só permanecem as linhas que atendem aos dois pontos, nessa ordem.
7. É possível continuar escolhendo pontos, refinando progressivamente as linhas.

DADOS
- OpenStreetMap para mapa base e relações de transporte público.
- Overpass API para consulta das relações type=route + route=bus em Mauá.
- O protótipo depende da qualidade/completude do cadastro do OSM.

TEMPO REAL
O arquivo contém um objeto RealtimeProvider e uma função refreshVehicles().
Quando houver uma API oficial ou feed GTFS-Realtime, basta adaptar fetchVehicles() para retornar:

[{ id, lat, lon, routeRef, bearing, timestamp }]

A atualização é executada imediatamente e depois a cada 30 segundos, mas somente após uma localização ou endereço ser confirmado com sucesso. A camada visual de veículos já está separada da camada de pontos e rotas. Enquanto `fetchVehicles()` retornar uma lista vazia, nenhum veículo será exibido.


A versão atual pode consultar os pontos a partir da localização do navegador ou de um endereço informado em Mauá. A busca de endereço usa o serviço Nominatim do OpenStreetMap; a consulta pode ser repetida pelos botões do painel.

ESTRUTURA DO CÓDIGO

FRONTEND
- `frontend/index.html`: marcação da interface e ordem de carregamento dos scripts.
- `frontend/css/styles.css`: tema, layout do painel, mapa e comportamento responsivo.
- `frontend/js/config.js`: constantes de configuração, como centro inicial, raio de busca e endpoints.
- `frontend/js/state.js`: estado compartilhado da aplicação, incluindo pontos, linhas, seleção e localização.
- `frontend/js/dom.js`: atalhos para elementos da interface e atualização do status.
- `frontend/js/utils.js`: funções puras reutilizáveis, como distância, centralização de geometrias e rótulos.
- `frontend/js/api.js`: consultas ao Nominatim, geolocalização do navegador e consultas ao Overpass.
- `frontend/js/data.js`: conversão da resposta do Overpass para o modelo de pontos e linhas usado pelo mapa.
- `frontend/js/map.js`: criação do mapa Leaflet, camadas, ícones e marcadores de pontos.
- `frontend/js/render.js`: desenho de trajetos, lista de linhas, seleção e estados visuais dos marcadores.
- `frontend/js/interactions.js`: ações do usuário, busca por endereço, localização, seleção de pontos e painel móvel.
- `frontend/js/realtime.js`: ponto de extensão para veículos em tempo real; atualmente retorna uma lista vazia.
- `frontend/js/app.js`: inicialização dos listeners e do painel responsivo.

Os scripts são carregados em ordem no `index.html`. Como usam o escopo global do navegador, uma função só deve ser movida para outro arquivo se suas dependências continuarem carregadas antes dela.

BACKEND
- `backend/server.py`: servidor HTTP estático local. Ele publica somente a pasta `frontend` e não possui API própria neste momento.
- `start_server.py`: atalho compatível para iniciar `backend/server.py` a partir da raiz.

FLUXO PRINCIPAL
1. `app.js` registra os eventos dos botões, formulário e painel.
2. A busca de endereço chama `api.js`, que converte o endereço em coordenadas usando o Nominatim.
3. A localização confirmada gera uma consulta Overpass em `api.js`.
4. `data.js` normaliza pontos e relações de ônibus e atualiza `state.js`.
5. `map.js` exibe os pontos; `render.js` desenha rotas e atualiza as opções compatíveis após cada seleção.

COMO EVOLUIR
- Alterações visuais devem ficar em `styles.css` ou na marcação de `index.html`.
- Novas fontes de dados devem ser adicionadas em `api.js`, sem misturar requisições com renderização.
- Regras de normalização do OSM pertencem a `data.js`.
- Regras de seleção e desenho de trajetos pertencem a `render.js` e `interactions.js`.
- Uma integração de tempo real deve implementar `RealtimeProvider.fetchVehicles()` em `realtime.js` e iniciar sua atualização somente após uma localização ter sido confirmada.