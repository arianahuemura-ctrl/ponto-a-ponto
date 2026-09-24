MEU PONTO — MAUÁ BUS MAP (MBM)
============================

Aplicação web Django/Python + React/Vite/Leaflet.
Interface baseada nas oito imagens mockup1.png a mockup8.png do relatório PI2.
Android, APK e PWA permanecem fora desta etapa.

Instalar e iniciar
------------------
Requisitos: Python 3.12+ e Node.js 24/npm.

Na raiz do projeto:
  workon bus
  pip install -r requirements.txt
  python backend/manage.py migrate
  cd frontend
  npm ci
  npm run build
  cd ..
  python start_server.py

Passageiro: http://127.0.0.1:8000/
Administração: http://127.0.0.1:8000/admin/

Para criar um usuário administrativo, uma única vez:
  python backend/manage.py createsuperuser

Não há usuário ou senha padrão. O login da administração exige usuário da equipe
com permissão para alterar o controle da simulação (ou superusuário).

Se precisar criar o virtualenv: mkvirtualenv -p python3 bus
Com nvm instalado, execute nvm install && nvm use na raiz.

Telas do passageiro
------------------
A interface abre diretamente o ponto. Não há botão para ativar a simulação,
seletor de modos nem relógio controlável pelo passageiro.

- Início: mapa, ponto identificado e ações Ver linhas / Buscar destino.
- Linhas do ponto: cartões com códigos coloridos e próximas chegadas.
- Destino: pesquisa e seleção no mapa, lista de locais e confirmação.
- Linhas filtradas: opções que atendem origem/destino, incluindo trocas.
- Mapa conjunto: veículos e trajetos de diferentes linhas nas mesmas ruas.
- Detalhes: abas Horários, Itinerário e Mapa da linha, sequência de paradas
  e duração estimada. Viagens com troca indicam as linhas de cada trecho.
- Favoritos: destinos pessoais e linhas salvas no navegador.
- Mais: preferências de trocas, sinalização QR imprimível, dados e avaliação.

Os códigos visuais 101, 210, 307, 405, 511 e 703 identificam as linhas fictícias
do cenário. Não são apresentados como códigos oficiais da operação de Mauá.
Nomes de paradas, quantidade de linhas e tempos vêm dos dados disponíveis;
a interface não copia números contraditórios dos mockups ilustrativos.

Controle da simulação
--------------------
Entre em /admin/ e abra Controle da simulação → Simulação dos ônibus.

- Simulação ligada: habilita ou retira os dados operacionais fictícios.
- Relógio em movimento: avança o horário no servidor.
- Horário simulado: permite definir/reiniciar a hora, por exemplo 08:00:00.
- Velocidade: tempo normal, 15 vezes ou 60 vezes.

Salve a configuração para aplicar. As páginas dos passageiros consultam o
servidor a cada 3 segundos e recebem o mesmo relógio. A configuração inicial
é ligada e pausada às 08:00 para uma apresentação reproduzível.

Ao desligar, veículos e previsões simuladas desaparecem e a interface informa
que as previsões estão indisponíveis. Não existe um provedor operacional real
configurado. Paradas geográficas e favoritos continuam disponíveis.
Parâmetros de URL não permitem mudar o relógio nem ligar a simulação.

A configuração é persistida em SQLite. Reiniciar o Django não a apaga.
A administração também permite consultar e registrar avaliações.

Trajetos pelas ruas
------------------
Os mapas usam geometrias viárias densas, obtidas do OSRM sobre o OpenStreetMap,
armazenadas em backend/transit/data/route_geometry.json. As polilinhas acompanham
as ruas e os veículos percorrem essas mesmas geometrias. Não há fallback para
retas entre paradas quando falta um trecho.

Para atualizar as geometrias, com internet:
  python backend/manage.py refresh_route_geometry

O comando só substitui o arquivo quando todas as consultas terminam com sucesso.
Reinicie o Django depois da atualização. Um servidor OSRM próprio pode ser
informado com --endpoint.
O passageiro não depende de consultas OSRM durante o uso: a cópia local já está
incluída. O mapa de fundo OSM e a pesquisa de endereços exigem internet.

O perfil de roteamento é driving. As ruas são reais, mas o percurso calculado
é uma hipótese de demonstração, não um itinerário de ônibus validado pela
operadora. Horários e tempos continuam mockados, independentes da estimativa
de duração do OSRM.

QR Code
-------
Abra Mais → QR Code deste ponto para visualizar ou imprimir a sinalização.
O código contém uma URL que identifica a origem, sem exigir aplicativo ou GPS:
  http://127.0.0.1:8000/?stop=way%3A1410074325

Para testar em celular na mesma rede:
  export DJANGO_ALLOWED_HOSTS="localhost,127.0.0.1,IP_DO_COMPUTADOR"
  export PUBLIC_BASE_URL="http://IP_DO_COMPUTADOR:8000"
  python start_server.py 0.0.0.0:8000

Substitua IP_DO_COMPUTADOR pelo endereço local da máquina. No celular,
127.0.0.1 apontaria para o próprio aparelho. O navegador exige HTTPS ou localhost
para geolocalização; entrar pelo QR não exige geolocalização.
A sinalização informa seu caráter acadêmico, sem aprovação oficial presumida.

Desenvolvimento
---------------
Terminal 1, na raiz e com virtualenv:
  python backend/manage.py runserver 127.0.0.1:8000

Terminal 2:
  cd frontend
  npm run dev

Passageiro: http://127.0.0.1:5173
Administração: http://127.0.0.1:8000/admin/
Vite encaminha /api ao Django. Ao usar os arquivos compilados, reexecute
npm run build após alterações no frontend.

A consulta OSM anterior permanece em /explorar/, fora da navegação principal.
Ela depende de Nominatim/Overpass e não inventa horários para linhas reais.

API
---
GET /api/network/              Paradas, linhas disponíveis, ruas e estado.
GET /api/board/?origin=...     Chegadas e veículos no horário do servidor.
GET /api/journey/?origin=...&destination=...
                              Dijkstra com espera, trocas e geometrias dos trechos.
GET /api/demo/qr/ID_DA_PARADA/
GET /api/geocode/?address=...&state=SP
GET /api/nearby/?lat=...&lon=...
GET/POST /api/demo/evaluation/ Perguntas e envio de observações com CSRF.

O planejador aceita destino por lat/lon e max_transfers (0 a 4).
Os antigos aliases /api/demo/network, board e journey usam o mesmo estado
global; não oferecem ativação independente da simulação.

Persistência
------------
db.sqlite3 contém configuração, usuários administrativos e avaliações.
Não é versionado. Faça backup para preservar os registros da apresentação.

Exportar observações:
  python backend/manage.py export_evaluations > avaliacoes.json

Favoritos e preferências do passageiro ficam no navegador.
Testes usam bancos temporários e não gravam avaliações ou credenciais no banco
da apresentação.

Verificações
------------
Com virtualenv ativo:
  python backend/manage.py check
  python backend/manage.py test
  cd frontend
  npm test
  npx playwright install chromium
  npm run test:e2e

O teste de entrega do frontend requer build anterior. Os testes de navegador
compilam o React e iniciam Django na porta 18081 com banco e usuário temporários.
Capturas das telas são geradas em frontend/test-results/mockup-*.png.
Os testes bloqueiam os tiles externos para não depender de disponibilidade
do mapa; verificam as geometrias locais, o fluxo e a administração real.

Documentação
------------
docs/TELAS.md                 Correspondência entre mockups e interface.
docs/DADOS_E_CENARIOS.md      Proveniência, roteamento e roteiro de demonstração.
docs/IMPLEMENTACAO.md         Inventário dos requisitos implementados.

Publicação e limitações
----------------------
runserver é somente para desenvolvimento. Publicação exige WSGI, HTTPS e
serviço de arquivos estáticos, incluindo os assets React e estáticos do admin.
Variáveis: DJANGO_DEBUG, DJANGO_SECRET_KEY, DJANGO_ALLOWED_HOSTS,
PUBLIC_BASE_URL, OSM_USER_AGENT e MBM_DATABASE (caminho do SQLite).
Com DEBUG=0, configure uma chave própria.

Overpass usa raio de 1 km e cache de 5 min; Nominatim, cache de 24 h e intervalo
mínimo de 1,1 segundo neste processo. Configure OSM_USER_AGENT com contato.
Vários processos exigem cache/limite de consultas compartilhados.

Dados operacionais reais, validação com Osmar e instalação física de QR Codes
continuam dependendo de ações externas. Caminhadas são aproximações de distância,
sem validação de calçadas. Android permanece uma evolução futura.
