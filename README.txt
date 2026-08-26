MAPA DE ÔNIBUS DE MAUÁ — PROTÓTIPO

1. Opção simples: abra index.html no navegador.
2. Se o navegador bloquear requisições feitas a partir de file://, execute nesta pasta:

   python -m http.server 8000

   e abra http://localhost:8000

3. Clique em “Carregar dados de Mauá”.
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

Depois habilite a atualização periódica (setInterval). A camada visual de veículos já está separada da camada de pontos e rotas.


A versão atual solicita a localização e carrega automaticamente os pontos/linhas ao abrir. O botão serve para repetir a consulta.
