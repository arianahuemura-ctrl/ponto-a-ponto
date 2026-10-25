## Escopo atual do planejador híbrido: até dois ônibus preparados

A geração municipal materializa somente um ou dois ônibus (cotas 16/8).
Três ônibus não são compostos nem materializados por esse fluxo. A aplicação consulta
os candidatos preparados e, se não houver alternativa válida ou os artefatos não
estiverem disponíveis, usa o planejador por rodadas, que mantém até três ônibus.
Não se executa RAPTOR para complementar uma lista válida de até dois ônibus.
Somente as categorias 1 e 2 precisam estar concluídas para liberar um par.

Os bancos materializados usam a versão 2 de assinatura. O setup preserva os arquivos
anteriores com sufixo `.obsolete-*` antes de reconstruir; não mistura o escopo antigo
com o novo. `--route-heuristics` continua em saída separada e aplica a poda geográfica
às categorias 1 e 2; a regra de exclusão da terceira categoria deixou de ser necessária
na geração municipal. Os comandos experimentais de comparação e os registros 16/8/4
abaixo documentam a investigação anterior, não o escopo atual do setup e da aplicação.

# Ponto a Ponto (PaP)

**Deslocamento facilitado entre origem e destino.**

Protótipo acadêmico do Projeto Integrador em Computação II da UNIVESP, iniciado com o contexto do transporte público de Mauá e com navegação integrada ao cadastro GTFS de São Paulo. O QR Code identifica a parada física e inicia a consulta no navegador, sem exigir instalação de aplicativo ou conhecimento prévio do nome do ponto ou da linha. O passageiro pode consultar as linhas, escolher um destino e comparar viagens. Utiliza **Django/Python**, **React/Vite** e **Leaflet**, com dados geográficos do OpenStreetMap.

O cadastro de paradas, linhas, variantes e documentos públicos é importado de `fonts/` para `db.sqlite3`. O cenário demonstrativo usa linhas, horários e veículos **simulados**, controlados pela administração e identificados separadamente das fontes reais. Os trajetos destacam as ruas do OSM; ainda não são itinerários validados pela operadora.

## São Paulo: navegação e destino da sessão

A página inicial abre a navegação de passageiros em São Paulo.

1. Configure `SPTRANS_TOKEN` no `.env` da raiz. O Django lê essa chave no início; reinicie o servidor após substituí-la. A chave não é enviada ao navegador. Teste o acesso com `python backend/manage.py check_sptrans`.
2. Ative o ambiente Python e execute `python backend/manage.py import_sptrans`. O comando indexa `fonts/sptrans_gtfs/` em `sptrans.sqlite3`, separado do banco da demonstração. Repita ao substituir o GTFS.
3. Compile com `npm --prefix frontend run build` e inicie o servidor normalmente.
4. Acesse `/`: a primeira etapa é **Selecionar local de embarque**. Toque em uma parada para abrir a lista de próximos ônibus; nessa janela também é possível salvar o embarque nos favoritos.
5. Toque em **Selecionar destino** para voltar ao mapa e escolher outra parada ou um favorito. A lista passa a mostrar apenas os ônibus da rota calculada, na ordem dos embarques, incluindo até duas trocas. **Alterar destino**, **Cancelar seleção** e **Cancelar viagem** permitem retomar ou encerrar o planejamento.
6. A lupa busca o endereço da etapa atual (embarque ou destino). Após três caracteres, oferece sugestões de ruas e lugares com bairro e município quando disponíveis. Sem número, selecione a rua para enquadrar suas paradas no mapa e escolher uma delas. Com número antes ou depois do nome da rua, confirme a parada sugerida. A distância exibida até o endereço é em linha reta.

O autocomplete utiliza Photon/Komoot sobre dados OpenStreetMap, com espera de 500 ms após digitar, cancelamento de consultas anteriores e cache de 10 minutos no servidor. O texto pesquisado é enviado a esse provedor externo. Quando o bairro não consta nos dados, a interface informa isso. O serviço público pode ficar indisponível; a seleção pelo mapa continua disponível.

A origem e o destino corrente ficam em `sessionStorage`, restritos à sessão da aba. Favoritos ficam em `localStorage`. **Cancelar viagem** limpa a sessão, preservando os favoritos. Um QR Code define a origem e mantém o destino se aberto na mesma sessão.

Enquanto a lista está aberta, as previsões são atualizadas a cada 30 segundos. Sem previsão, o aplicativo identifica os dados do GTFS como programação ou estimativa, sem apresentá-los como chegadas ao vivo. O cálculo respeita calendário, exceções, sentido e sequência das paradas. A rota escolhida considera tempos estimados do GTFS; as previsões atuais de uma parada de troca devem ser conferidas novamente ao chegar.

As correspondências com o Olho Vivo exigem código completo da linha e terminal de destino compatíveis. Paradas precisam pertencer à linha e ter correspondência única a até 15 metros (ou o mesmo código nessa área). Não se presume que os identificadores do GTFS sejam os mesmos da API. Quando a correspondência é ambígua ou a API não cobre uma parada, não há previsão em tempo real. Posições com mais de 3 minutos e previsões com posição capturada há mais de 5 minutos são descartadas. Em terminais, o painel limita a consulta ao vivo a 12 linhas e interrompe novas consultas após 8 segundos. Linhas não consultadas ficam identificadas na lista.

A informação operacional depende de uma credencial aceita pela SPTrans e da cobertura da API para a linha e a parada. Confira sua instalação com `python backend/manage.py check_sptrans`; autenticação bem-sucedida não garante previsões para todas as paradas. Veja [como obter o token](#como-obter-o-token-da-sptrans).

Documentação oficial: [API Olho Vivo](https://www.sptrans.com.br/desenvolvedores/api-do-olho-vivo-guia-de-referencia/documentacao-api/).

## Estado do projeto

- **Protótipo web:** Django e React, com catálogo SQLite, planejamento de viagens e simulação controlada no admin.
- **Dados operacionais:** tempos, horários e veículos da demonstração são simulados. Importar catálogos públicos não disponibiliza rastreamento real nem valida os itinerários.
- **Design e documentação:** mockup interativo em Figma em desenvolvimento paralelo; os PDFs versionam seus fontes LaTeX e utilizam imagens conceituais compartilhadas.
- **Comunidade externa:** entrevista e esclarecimentos de Osmar sobre bilhetagem registrados; a avaliação da solução atual e os testes com passageiros continuam pendentes.
- **Escopo futuro:** integração com fornecedores, eventual aplicativo Android e investigação de informações agregadas de origem e destino. Uma consulta de destino indica intenção, não comprova embarque ou desembarque.

O Cittamobi já oferece consulta por destino e planejamento com conexões. A contribuição investigada pelo PaP concentra-se em facilitar a identificação da parada no ambiente físico e o acesso contextualizado às informações.

## Índice

- [Estado do projeto](#estado-do-projeto)
- [Instalação](#instalação)
- [Iniciar a aplicação](#iniciar-a-aplicação)
- [Como usar o admin](#como-usar-o-admin)
- [Como usar o sistema](#como-usar-o-sistema)
- [Acessar pelo celular e QR Code](#acessar-pelo-celular-e-qr-code)
- [Desenvolvimento](#desenvolvimento)
- [Testes](#testes)
- [Dados e manutenção](#dados-e-manutenção)
- [Configuração](#configuração)
- [Como obter o token da SPTrans](#como-obter-o-token-da-sptrans)
- [API e documentação](#api-e-documentação)
- [Importação de fontes públicas](#importação-de-fontes-públicas)
- [Geolocalização aproximada das paradas](#geolocalização-aproximada-das-paradas)
- [Relatório, mockup e entrevistas](#relatório-mockup-e-entrevistas)

## Instalação

### 1. Requisitos

| Componente | Requisito |
| --- | --- |
| Sistema | Debian/Ubuntu com APT; pacotes conferidos no Ubuntu 26.04 |
| Python | 3.12 ou superior |
| Node.js | 24, conforme [.nvmrc](.nvmrc) |
| npm | Fornecido com o Node.js instalado pelo nvm |
| Banco | SQLite, integrado ao Python; não exige servidor separado |
| Navegador | Navegador atualizado com JavaScript |

A instalação requer internet. Durante o uso, o mapa de fundo e a busca de endereços também precisam de conexão. Os cenários simulados e as geometrias dos trajetos já estão incluídos no projeto.

Os arquivos de dependências têm funções distintas:

| Arquivo | Instalação |
| --- | --- |
| [requirements.system](requirements.system) | Pacotes do sistema via APT |
| [requirements.txt](requirements.txt) | Bibliotecas Python dentro do ambiente virtual |
| [requirements-dev.txt](requirements-dev.txt) | Dependências Python e ferramenta de cobertura para desenvolvimento |
| [frontend/package-lock.json](frontend/package-lock.json) | Bibliotecas JavaScript com `npm ci` |

### 2. Executar a instalação consolidada

Para instalar todos os componentes previstos pelo setup, execute como usuário normal:

```bash
./setup.sh --all
```

A opção inclui `--system --node --dev --walking --routes --demo --browser --admin`, além
das etapas padrão de instalação e importação GTFS. A ordem respeita as dependências:

1. Pacotes APT, incluindo Python/venv, curl e ferramentas de importação.
2. nvm e Node.js conforme `.nvmrc`.
3. Ambiente Python, dependências da aplicação, cobertura e processamento OSM.
4. `.env`, migrações Django e índice GTFS.
5. Grafo temporal, tabelas de custos, ligações diretas e índice reverso.
6. Rede OSM/OSRM foot local e matriz de caminhadas a 4,5 km/h.
7. Componentes de ônibus + caminhada e materialização física municipal TOP 16/8/4.
8. Demonstração de Mauá, dependências JavaScript, frontend e Chromium.
9. Verificação Django e criação interativa do administrador, caso ainda não exista.

O `sudo` pode solicitar senha. O GTFS precisa estar em `fonts/sptrans_gtfs/` ou ser
indicado por `--gtfs-source DIR`. O `.env`, o índice GTFS existente e o administrador
existente são preservados. `--refresh-gtfs` continua sendo necessário para reimportar
um índice; `--all --skip-gtfs` é rejeitado para não declarar instalação completa
sem essa etapa. As falhas interrompem a execução antes das etapas dependentes.

A instalação e a geração são controladas por `setup.sh`. Internamente, o Makefile
ordena grafo → diretas/reversas → caminhadas → componentes → materialização.
Cada alvo valida a procedência/versionamento dos bancos antes de reutilizá-los;
não depende apenas do horário de modificação. Não é necessário executar `make`
ou comandos Django manualmente. Falhas impedem a execução das etapas seguintes.

Docker não é mais necessário. Quando as caminhadas precisam ser geradas, o setup
prepara o OSRM 6.0.0 nativo em `.cache/osrm-6.0.0`, compila com dois processos,
recorta o OSM, executa extract → partition → customize com o perfil foot e inicia
um processo temporário em localhost. O processo é encerrado ao terminar ou falhar.
`--system --routes` instala as dependências de compilação via APT; a compilação
ocorre como usuário normal. Para usar um PBF já disponível:

```bash
./setup.sh --all --osm-pbf /caminho/sudeste.osm.pbf
```

A geração de toda a cidade é uma tarefa pesada, que pode levar muito tempo e consumir
bastante disco. Há reserva mínima de 5 GiB e limite de 600 segundos por categoria
na materialização. Artefatos válidos são reutilizados; pares concluídos são ignorados
na retomada. Uma materialização incompatível é renomeada com sufixo `.obsolete-DATA`
antes da reconstrução. Categorias que atingirem o limite ficam pendentes: o setup
**não anuncia sucesso**. Execute novamente para retomar ou amplie o limite:

```bash
./setup.sh --artifacts-only --route-seconds 1800 --min-free-gib 10
```

O token SPTrans e o GTFS continuam sendo fornecidos separadamente. O preparo não
consulta a API Olho Vivo e nunca usa o roteador público para a matriz municipal.

Para instalar somente os requisitos da aplicação:

Na raiz do repositório, execute como usuário normal:

```bash
./setup.sh --system --node
```

`--system` instala os pacotes de [requirements.system](requirements.system) via
APT e solicita `sudo`. `--node` instala/carrega o nvm e prepara o Node.js indicado
em [.nvmrc](.nvmrc). O nvm instalado pelo script fica disponível nesta execução;
os comandos de desenvolvimento em novos terminais podem exigir carregar
`source "${NVM_DIR:-$HOME/.nvm}/nvm.sh"`.

Se Python >= 3.12, suporte a `venv` e Node.js 24 já estão disponíveis:

```bash
./setup.sh
```

O [setup.sh](setup.sh) executa, em ordem:

1. Verifica Python e Node.js.
2. Cria ou reutiliza `.venv` e instala `requirements.txt`.
3. Cria `.env` a partir de `.env.example` somente quando ele não existe.
4. Aplica as migrações Django sem remover dados existentes.
5. Importa `fonts/sptrans_gtfs/` se o índice GTFS configurado ainda não existe.
6. Executa `npm ci`, compila o frontend e verifica a configuração Django.

O script pode ser chamado de outro diretório; os caminhos relativos informados
nas opções são resolvidos a partir da raiz do projeto. É possível executá-lo
novamente após uma interrupção. O `.env` e os bancos existentes são preservados,
embora as migrações atualizem o esquema Django. O frontend compilado é atualizado.

O terminal mostra uma barra com percentual, etapas concluídas/total, etapa atual
e tempo decorrido em segundos. A contagem considera apenas as opções selecionadas
e avança depois de cada etapa bem-sucedida (ou da reutilização válida dos dados).
**O percentual é de etapas, não de tempo restante.** Durante a geração longa dos
artefatos, os logs continuam mostrando origens e categorias processadas; a barra
principal só avança quando essa etapa termina. Uma falha não apresenta 100%.
A saída usa linhas simples, legíveis também quando redirecionadas para um arquivo.

### 3. Opções de instalação

```bash
./setup.sh --help
./setup.sh --gtfs-source /caminho/gtfs
./setup.sh --skip-gtfs
./setup.sh --refresh-gtfs
./setup.sh --admin
./setup.sh --demo
./setup.sh --browser
./setup.sh --dev
./setup.sh --walking
```

| Opção | Efeito |
| --- | --- |
| `--all` | Instala tudo e gera os artefatos municipais na ordem das dependências; só cria administrador se ainda não houver. |
| `--routes` | Instala a aplicação e prepara/retoma artefatos; usa OSRM nativo para caminhadas. |
| `--artifacts-only` | Prepara/retoma artefatos com a `.venv` e dependências já instaladas, sem reinstalar frontend/Python. |
| `--rebuild-artifacts` | Força reconstrução e preserva bancos anteriores em `artifacts-backup-DATA/`; combine com `--artifacts-only`. |
| `--route-seconds N` | Prazo por categoria na materialização (600 por padrão). |
| `--min-free-gib N` | Reserva mínima de disco (5 GiB por padrão). |
| `--osm-pbf FILE` | Usa extrato OSM local no preparo da rede pedestre, evitando o download. |
| `--gtfs-source DIR` | Usa outra pasta de arquivos GTFS `.txt`. |
| `--skip-gtfs` | Adia a importação; a navegação SPTrans precisa do índice para funcionar. |
| `--refresh-gtfs` | Reimporta o GTFS mesmo com índice existente. Depois, regenere os artefatos de busca. |
| `--admin` | Solicita interativamente nome, e-mail e senha para criar um administrador. |
| `--demo` | Importa fontes públicas e a demonstração histórica de Mauá. |
| `--browser` | Instala Chromium e dependências de sistema para os testes Playwright; pode solicitar `sudo`. |
| `--dev` | Instala também `coverage` para medir a suíte Python. |
| `--walking` | Instala `requirements-walking.txt`, usado no pré-processamento OSM opcional. |

As opções podem ser combinadas, exceto `--skip-gtfs` com `--refresh-gtfs`, `--all` ou `--routes`.
Para selecionar outro Python ao criar `.venv`, use
`PYTHON_BIN=python3.14 ./setup.sh`. Um `.venv` já existente é reutilizado e precisa
ter Python >= 3.12.

### 4. Dados e credenciais

Se `fonts/sptrans_gtfs/` estiver ausente, obtenha o GTFS na
[área oficial da SPTrans](https://www.sptrans.com.br/desenvolvedores/) e extraia os
arquivos `.txt` nessa pasta. O script não baixa o GTFS nem exige token para importá-lo.
A importação respeita `SPTRANS_DATABASE`, conforme a configuração Django.

Preencha `SPTRANS_TOKEN` no `.env` conforme [as instruções abaixo](#como-obter-o-token-da-sptrans)
para habilitar o Olho Vivo. O script não imprime nem solicita a credencial.
A localização de teste é informada por `location=latitude,longitude` ou pelos parâmetros separados `latitude` e `longitude` na URL.
**Não existe usuário ou senha padrão.** Use `--admin` somente se precisar criar
um administrador.

A instalação padrão (`./setup.sh`) prepara somente a aplicação. Use `--all` ou
`--routes` para incluir os artefatos de busca. `--routes` instala também as dependências
Python de caminhada; as dependências nativas são instaladas com `--system --routes`. Consulte
[Planejador de conexões](#planejador-de-conexões--branch-featbusca-bidirecional)
para os detalhes dos artefatos. Sem artefatos disponíveis, a aplicação mantém o
fallback SPTrans/RAPTOR, mas isso não satisfaz a conclusão de `--all`.

O script não inicia o servidor. Após terminar, siga as instruções abaixo.

## Iniciar a aplicação

Na raiz, com as dependências instaladas:

~~~bash
source .venv/bin/activate
python start_server.py
~~~

| Acesso | Endereço |
| --- | --- |
| São Paulo — passageiro | http://127.0.0.1:8000/ |
| Administração | http://127.0.0.1:8000/admin/ |

Mantenha o terminal aberto. Para encerrar o servidor, pressione **Ctrl+C**.

Nas próximas execuções, basta ativar o ambiente e iniciar o servidor. Não é necessário reinstalar dependências ou recompilar o frontend quando não houve mudanças. Node.js não é necessário para servir um frontend já compilado.

Se a porta 8000 estiver ocupada:

~~~bash
python start_server.py 127.0.0.1:8001
~~~

Nesse caso, acesse a aplicação e o admin na porta 8001.

## Como usar o admin

### Entrar no painel

1. Abra http://127.0.0.1:8000/admin/.
2. Entre com o usuário criado por `createsuperuser`.
3. Abra **Controle da simulação → Simulação dos ônibus**.

Se ainda não houver um registro, abra a página do passageiro uma vez para inicializar a configuração, ou adicione o controle no admin.

Além de superusuários, membros da equipe podem acessar o painel quando recebem as permissões necessárias para visualizar e alterar o controle.

### Ligar, desligar e ajustar a simulação

| Campo | Função |
| --- | --- |
| **Simulação ligada** | Disponibiliza linhas, veículos e previsões fictícias |
| **Relógio em movimento** | Faz o horário simulado avançar no servidor |
| **Horário simulado** | Define a hora do cenário, por exemplo `08:00:00` |
| **Velocidade** | Escolhe tempo normal, 15 vezes ou 60 vezes |

Clique em **Salvar** para aplicar.

Para uma apresentação com veículos em movimento, marque **Simulação ligada** e **Relógio em movimento**. Para repetir um cenário, mantenha a simulação ligada, desmarque o movimento do relógio e ajuste a hora para **08:00:00**.

A configuração inicial é **ligada e pausada às 08:00**. Ela fica salva no banco e é compartilhada por todos os passageiros. As páginas consultam o servidor a cada três segundos.

Ao desligar a simulação, veículos e previsões desaparecem. O sistema informa que as previsões estão indisponíveis, pois ainda não há um provedor operacional real configurado. O passageiro não possui comandos para ligar a simulação ou alterar o relógio.

### Consultar avaliações

A área de avaliações do admin permite consultar e registrar as observações da demonstração. Também é possível exportá-las pela linha de comando:

~~~bash
python backend/manage.py export_evaluations > avaliacoes.json
~~~

## Como usar o sistema

As instruções desta seção descrevem a demonstração de Mauá (`/?city=maua`). Para São Paulo, siga a seção “São Paulo: navegação e destino da sessão”.

### Consultar um ponto e seus ônibus

1. Abra a aplicação ou leia o QR Code de uma parada.
2. Confira o ponto identificado na tela **Início**.
3. Toque em **Ver linhas deste ponto** ou **Horários**.
4. Compare as linhas e os tempos de chegada apresentados nos cartões.

Para mudar a origem, use **Trocar ponto** e selecione uma parada no mapa. A opção **Minha localização** procura a parada do recorte mais próxima da posição informada pelo dispositivo.

### Escolher um destino

1. Toque em **Buscar destino no mapa**.
2. Selecione uma parada, toque em outro local do mapa ou pesquise um endereço.
3. Confira o local e toque em **Confirmar destino**.
4. Compare as alternativas filtradas e o tempo estimado até a chegada.

O planejamento utiliza Dijkstra no Django e considera horários, espera e eventuais trocas de ônibus. Para locais fora das paradas, considera paradas do recorte a até 500 metros e uma caminhada aproximada.

Em **Mais → Preferência de viagem**, é possível limitar as trocas ou escolher somente viagens diretas. Quando não há conexão, a interface informa essa condição.

### Ver os trajetos e acompanhar os veículos

Na lista de próximos ônibus de um ponto, mantenha uma linha pressionada por cerca de 0,65 s, sem arrastar, para ativar a seleção múltipla. A primeira linha fica marcada; selecione ou desmarque as demais com cliques/toques simples nas linhas ou nas caixas do canto superior esquerdo. Também é possível iniciar pelo botão “Selecionar linhas para acompanhar”, acessível pelo teclado. Use “Ver mapa” para acompanhar o próximo veículo com previsão de cada linha selecionada e seu percurso até o ponto. As consultas são atualizadas a cada 5 s; uma linha sem previsão/posição disponível é indicada no painel, sem impedir as demais. Volte à lista para ajustar a seleção ou use “Limpar seleção”.


- **Ver essas linhas no mapa** reúne as alternativas em um único mapa.
- Toque em uma linha para abrir seus detalhes.
- **Horários** mostra próximas partidas e duração estimada.
- **Itinerário** mostra a sequência de paradas e as trocas.
- **Mapa da linha** destaca as ruas percorridas.
- Quando disponível, **Acompanhar esta viagem** mantém a viagem escolhida enquanto o relógio administrativo avança.

### Salvar favoritos

Para um destino: escolha o local, abra **Favoritos**, informe um nome como Casa, Trabalho ou Escola e salve. Depois, toque no favorito para consultar o trajeto a partir da origem atual.

Para uma linha: abra os detalhes e toque no coração **Favoritar**. Ela também aparecerá em **Favoritos**.

Os dados ficam neste navegador, sem conta ou sincronização entre aparelhos. É possível remover os favoritos na mesma tela.

### Registrar observações

Abra **Mais → Registrar avaliação**, preencha o campo e envie. As observações ficam armazenadas no servidor para consulta pela equipe no admin.

## Acessar pelo celular e QR Code

Para acesso temporário pela internet com Gunicorn isolado em 8001 e Cloudflare Tunnel, consulte [Acesso público temporário](docs/ACESSO_PUBLICO_TEMPORARIO.md).

Em **Mais → QR Code deste ponto**, visualize ou imprima a sinalização. O QR Code identifica a origem pela URL, sem exigir aplicativo, GPS ou conhecimento prévio do nome da linha:

http://127.0.0.1:8000/?stop=way%3A1410074325

Para testar com um celular na mesma rede, substitua `IP_DO_COMPUTADOR` pelo endereço local da máquina e execute na raiz:

~~~bash
export DJANGO_ALLOWED_HOSTS="localhost,127.0.0.1,IP_DO_COMPUTADOR"
export PUBLIC_BASE_URL="http://IP_DO_COMPUTADOR:8000"
python start_server.py 0.0.0.0:8000
~~~

No celular, acesse essa URL ou escaneie o QR gerado após a configuração. `127.0.0.1` no celular aponta para o próprio aparelho, não para o computador.

A geolocalização exige HTTPS ou localhost. A entrada pelo QR e a escolha manual do destino funcionam sem geolocalização. A sinalização identifica o caráter acadêmico do protótipo.

## Desenvolvimento

Use dois terminais para atualizar o React automaticamente durante a edição.

**Terminal 1 — Django, na raiz:**

~~~bash
source .venv/bin/activate
python backend/manage.py runserver 127.0.0.1:8000
~~~

**Terminal 2 — React, a partir da raiz:**

~~~bash
nvm use
cd frontend
npm run dev
~~~

- Frontend: http://127.0.0.1:5173/
- Admin: http://127.0.0.1:8000/admin/

O Vite encaminha `/api` ao Django na porta 8000. O explorador OSM anterior permanece em `/explorar/`, fora da navegação principal; suas consultas dependem de Nominatim e Overpass.

## Interface responsiva e aparência

A interface do passageiro se adapta a celulares, tablets e computadores. Em telas maiores, a escolha do destino e a consulta de veículos apresentam o mapa ao lado do painel de informações. Estão disponíveis os fluxos de origem pelo QR Code, linhas, destino, alternativas, veículos, detalhes da viagem, paradas, favoritos e cadastro público.

O botão de sol/lua no cabeçalho alterna entre os modos claro e escuro. Em **Mais → Aparência**, a opção **Automático** acompanha o tema do dispositivo. A escolha fica salva neste navegador; quando o armazenamento está bloqueado, funciona durante a sessão. Os avisos de simulação permanecem visíveis em ambos os temas.

## Testes

Com as dependências instaladas e o frontend compilado, execute na raiz:

~~~bash
source .venv/bin/activate
python backend/manage.py check
python backend/manage.py test transit
~~~

Para os testes JavaScript e de navegador:

~~~bash
nvm use
cd frontend
npm test
npx playwright install --with-deps chromium
npm run test:e2e
~~~

O comando `install --with-deps` prepara o Chromium e os pacotes de sistema adicionais **somente para os testes de navegador**; pode solicitar senha de administrador. Essas dependências são gerenciadas pela versão instalada do [Playwright](https://playwright.dev/docs/browsers#install-system-dependencies) e não são necessárias para iniciar o servidor Django.

Os testes de navegador compilam o React, iniciam Django na porta 18081 e usam um banco temporário com um administrador de teste. Não alteram usuários ou avaliações da instalação principal. O ambiente Python deve continuar ativo.

Capturas são geradas em `frontend/test-results/mockup-*.png` e `frontend/test-results/responsive-*.png`. Os testes responsivos percorrem os fluxos em larguras de 320, 390, 768, 844 e 1440 pixels, verificando navegação, ausência de transbordamento horizontal e persistência do tema. Os tiles externos são bloqueados nesses testes; as geometrias locais e os fluxos continuam sendo verificados.

### Cobertura reproduzível

Instale as ferramentas de desenvolvimento com `./setup.sh --dev` ou, no ambiente
Python já ativo, `python -m pip install -r requirements-dev.txt`.

Na raiz, com o ambiente Python ativo:

```bash
python -m coverage run backend/manage.py test transit
python -m coverage report
python -m coverage html
python -m coverage json
```

O backend inclui módulos da aplicação, API, planejadores e comandos administrativos.
Somente os próprios testes, migrações geradas e o servidor auxiliar dos testes são
excluídos. A configuração [.coveragerc](.coveragerc) mede linhas e ramos e faz a
verificação falhar abaixo de 71% na métrica combinada do Coverage.py. O relatório
JSON separa os percentuais de linhas e ramos; o HTML fica em
`coverage/backend/index.html`.

Para medir o frontend completo, incluindo componentes React, prepare o Chromium
com `./setup.sh --dev --browser` se ainda não estiver instalado. Mantenha o ambiente
Python ativo e use Node.js 24:

```bash
cd frontend
npm ci
npm test
npm run test:coverage
```

A cobertura do frontend é coletada durante os testes Playwright, inclusive nos
contextos móveis, com o Django e banco descartáveis. Inclui todos os arquivos
JavaScript/JSX de `src`, mesmo os não executados, exceto os próprios testes.
As respostas externas simuladas verificam o comportamento da interface sem depender
da disponibilidade do Olho Vivo, mapas ou geocodificador. Os três testes de
localização por URL usam o endpoint Django real do servidor de testes.

`npm test` executa adicionalmente os testes unitários JavaScript; seus contadores
não são somados à cobertura de navegador. O comando de cobertura exige pelo menos
71% em linhas, instruções, funções e ramos. Gera
`frontend/coverage/index.html` e `frontend/coverage/coverage-summary.json` e recompila
o frontend sem instrumentação ao terminar, inclusive quando a suíte falha.
Os relatórios e contadores ficam fora do Git. O limiar é agregado por camada;
não significa que cada arquivo individual atingiu 71%.

Scripts shell, SQL e estilos CSS não entram nesses percentuais. Uma linha executada
não garante que todos os comportamentos foram verificados; os testes de interface
continuam necessários junto aos testes de regras e contratos.

## Dados e manutenção

### Banco e preferências

`db.sqlite3` contém o catálogo de paradas e linhas, documentos de origem, execuções e estimativas de geolocalização, cenário demonstrativo, configuração da simulação, usuários administrativos e avaliações. O arquivo não é versionado; preserve uma cópia ao mover ou reinstalar o projeto. Favoritos e preferências dos passageiros ficam nos respectivos navegadores.

### Atualizar trajetos

As geometrias estão em [backend/transit/data/route_geometry.json](backend/transit/data/route_geometry.json). Foram calculadas sobre as ruas do OSM via OSRM; os veículos percorrem essas mesmas curvas.

Para atualizar a cópia local:

~~~bash
python backend/manage.py refresh_route_geometry
~~~

O comando exige internet e só substitui o arquivo quando todas as consultas terminam com sucesso. Reinicie o Django depois da atualização. A opção `--endpoint` permite indicar outro servidor OSRM.

O perfil utilizado é `driving`. As ruas são reais, mas os trajetos ainda precisam de validação pela operadora. Horários e durações permanecem mockados. Caminhadas são aproximadas, sem validação de calçadas.

## Configuração

O backend e os comandos de artefatos usam `python-dotenv`. A precedência é `.env.example` → `.env` → variáveis exportadas no ambiente do processo. O exemplo fornece os padrões; o `.env` pode conter apenas as diferenças locais. Valores vazios explícitos também sobrescrevem o exemplo. Aspas, comentários e o prefixo `export` seguem a sintaxe do dotenv. A expansão `${VAR}` está desativada: os valores são literais, inclusive tokens. Os arquivos nunca são executados como comandos shell.

| Variável no `.env` | Padrão e função |
| --- | --- |
| `SPTRANS_TOKEN` | Vazio. Credencial privada do Olho Vivo, usada apenas pelo backend. Sem ela, não há consultas operacionais ao vivo. |
| `SPTRANS_DATABASE` | `sptrans.sqlite3` na raiz. Caminho absoluto alternativo do índice GTFS; use a mesma configuração na importação e no servidor. |
| `SPTRANS_PLANNER` | `connections`. Usa o planejador materializado com fallback SPTrans/RAPTOR; `raptor` usa somente o anterior. |
| `SPTRANS_CONNECTION_API_BUDGET` | `20`. Orçamento suave, em segundos, das consultas operacionais do novo planejador. |

A posição de teste do passageiro é configurada exclusivamente pelos parâmetros
`latitude` e `longitude` na URL, conforme a seção [Localização do passageiro em São Paulo](#localização-do-passageiro-em-são-paulo).
Sem esses parâmetros, a aplicação solicita o GPS do navegador.

Após editar o `.env`, reinicie o Django e recarregue a página. Não é necessário recompilar o frontend. Não publique o arquivo nem coloque o token em variáveis `VITE_*`, capturas ou URLs do navegador.

As configurações abaixo também podem ser definidas no `.env` ou no ambiente do processo:

| Variável | Padrão e função |
| --- | --- |
| `DJANGO_DEBUG` | `1` para desenvolvimento; `0` desativa DEBUG. |
| `DJANGO_SECRET_KEY` | Chave local de desenvolvimento; defina uma chave própria ao desativar DEBUG. |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1,[::1]`. Hosts separados por vírgulas, sem espaços, protocolo ou porta. |
| `PUBLIC_BASE_URL` | Vazio. URL pública usada nos QR Codes; para celular, deve ser acessível pelo aparelho. |
| `OSM_USER_AGENT` | `MauaBusMap/0.2 (local academic prototype)`. Identificação nas consultas geográficas externas. |
| `MBM_DATABASE` | `db.sqlite3` na raiz. Banco Django, distinto do índice GTFS. |

Exemplo para acesso pela mesma rede, substituindo o IP pelo endereço do computador:

~~~bash
export DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,192.168.1.10
export PUBLIC_BASE_URL=http://192.168.1.10:8000
python start_server.py 0.0.0.0:8000
~~~

No celular, abra `http://192.168.1.10:8000/`. O endereço `127.0.0.1` no celular aponta para o próprio aparelho.

### Como obter o token da SPTrans

1. Abra a [área de desenvolvedores da SPTrans](https://www.sptrans.com.br/desenvolvedores/) e cadastre-se, ou entre na conta existente.
2. Confirme o cadastro pelo link enviado por e-mail. Se ele não chegar, confira spam e o endereço cadastrado; a confirmação é uma etapa exigida pelo portal.
3. No perfil, acesse **Meus Aplicativos**, cadastre o aplicativo e copie a chave de acesso gerada.
4. Coloque essa chave em `SPTRANS_TOKEN` no `.env` da raiz e reinicie o backend.
5. Com o ambiente Python ativo, verifique a autenticação e a consulta de posições:

~~~bash
python backend/manage.py check_sptrans
~~~

Em caso de sucesso, o comando mostra `API acessível`, a referência de horário e quantidades de linhas e veículos, sem revelar o token. Uma consulta pode retornar poucos ou nenhum veículo. Se falhar, confira a chave, a confirmação da conta e a conexão; erros de rede não significam necessariamente token inválido. O backend faz a autenticação e gerencia a sessão da API.

Procedimento conforme o [guia oficial do Olho Vivo](https://www.sptrans.com.br/desenvolvedores/api-do-olho-vivo-guia-de-referencia/). A [documentação da API](https://www.sptrans.com.br/desenvolvedores/api-do-olho-vivo-guia-de-referencia/documentacao-api/) descreve a autenticação, as posições e as previsões. O token dá acesso à API; o cadastro GTFS é importado separadamente.

`runserver` é destinado ao desenvolvimento. Uma publicação exige servidor WSGI, HTTPS e serviço de arquivos estáticos para React e admin.

Overpass usa raio de 1 km e cache de cinco minutos. Nominatim usa cache de 24 horas e intervalo mínimo de 1,1 segundo por processo. Uma instalação com vários processos exige controle compartilhado dessas consultas.

## API e documentação

| Método e endpoint | Conteúdo |
| --- | --- |
| `GET /api/network/` | Paradas, linhas, geometrias e estado |
| `GET /api/board/?origin=...` | Chegadas e veículos no horário do servidor |
| `GET /api/journey/?origin=...&destination=...` | Viagens, trocas e trechos; aceita também destino por `lat/lon` e `max_transfers` |
| `GET /api/demo/qr/ID_DA_PARADA/` | QR Code da parada |
| `GET /api/geocode/?address=...&state=SP` | Busca de endereço |
| `GET /api/nearby/?lat=...&lon=...` | Consulta de pontos e linhas OSM |
| `GET/POST /api/demo/evaluation/` | Perguntas e envio de observações com CSRF |

Os antigos aliases `/api/demo/network/`, `/api/demo/board/` e `/api/demo/journey/` usam o mesmo estado global, sem ativação independente.

- [Telas e mockups](docs/TELAS.md)
- [Origem dos dados e cenários](docs/DADOS_E_CENARIOS.md)
- [Inventário da implementação](docs/IMPLEMENTACAO.md)

Os códigos visuais das linhas são ilustrativos. Integração operacional real, avaliação com Osmar e implantação física dos QR Codes dependem de etapas externas. Android, APK e PWA permanecem fora da implementação atual.


## Importação de fontes públicas

O banco SQLite é a fonte de dados da interface de passageiros, do catálogo e do planejamento.
Os JSONs antigos são usados somente para importar explicitamente o cenário demonstrativo;
não existe fallback silencioso para eles durante uma requisição.

Com seu ambiente ativo (`workon bus`, se utiliza virtualenvwrapper), execute na raiz:

```bash
# Coletar fontes públicas e importar os arquivos locais para o banco.
python backend/manage.py import_sources --download

# Reimportar os arquivos já coletados, sem internet.
python backend/manage.py import_sources

# Atualizar as respostas públicas preservadas em fonts/raw/.
python backend/manage.py import_sources --download --refresh

# Incluir/restaurar também o cenário fictício para apresentação.
python backend/manage.py import_sources --demo
```

A coleta preserva URL, data de acesso, SHA-256, tipo do documento e falhas. `Last-Modified`,
quando presente, refere-se ao arquivo; não é tratado como atualização de todo o serviço.
Downloads anteriores são reutilizados por padrão. Não apague `fonts/raw/` se pretende
reimportar offline. Os arquivos baixados e o SQLite ficam fora do Git; o coletor,
o manifesto e o recorte OSM são versionados. Os PDFs são preservados e seu texto é
extraído com `pdftotext`, fornecido por `poppler-utils` em `requirements.system`.

A reimportação atualiza registros por identificador da fonte e substitui a sequência
ordenada de cada variante sem duplicá-la. Uma parada pode ocorrer mais de uma vez
no mesmo percurso. Registros ausentes em uma coleta posterior não são excluídos
automaticamente: ausência numa página não comprova desativação de uma linha.
A validação de coordenadas, vínculos e checksums ocorre em transações.

Na aplicação, abra **Ver linhas deste ponto → Consultar cadastro de linhas**, ou
**Mais → Sobre os dados → Consultar linhas e pontos importados**. Pesquise por código,
destino ou fonte e selecione a variante para ver a sequência de paradas e o link
para o documento original. O catálogo continua disponível com a simulação desligada.
No `/admin/`, consulte **Stops**, **Routes** e **Source documents** para inspecionar
coordenadas, sequência, procedência, documentos e pendências.

### Cobertura e limites das fontes

- **Cittamobi:** catálogo municipal, identificadores de paradas e sequência por variante;
  informações de horários publicadas são preservadas, mas não viram previsões reais.
  As páginas coletadas não fornecem coordenadas numéricas das paradas; a etapa de geolocalização pode produzir estimativas identificadas separadamente.
- **Suzantur:** catálogo oficial e documentos individuais dos itinerários; mantidos
  separadamente para comparação com as variantes do Cittamobi.
- **Prefeitura:** itinerários por ruas das linhas 71, 75 e 76, com vigência indicada
  em 28/02/2026. Ruas não são convertidas automaticamente em pontos de embarque.
- **EMTU:** portal e consulta parcial por logradouro, com seus itinerários individuais;
  essa consulta não cobre todas as linhas intermunicipais de Mauá.
- **OSM:** recorte geográfico de 23/09/2026 em `fonts/osm.json`, com paradas e relações
  de linhas. As relações sem todos os membros não são consideradas trajetos completos.
- **PlanMob 2017, Moovit, Bus2 e Ônibus Online:** documentos de referência e conferência,
  pesquisáveis no admin; o endpoint de dados do painel Bus2 retornou HTTP 500 na coleta,
  embora sua página institucional estivesse disponível. Não geram associações de paradas ou coordenadas inferidas.

Registros sem coordenadas ficam no catálogo, não no mapa. Fontes distintas não são
fundidas por proximidade ou nomes semelhantes. Quantidades são registros/variantes,
não uma garantia de pontos físicos únicos nem de cobertura integral da cidade.
O planejamento e os veículos simulados continuam usando as seis linhas demonstrativas
importadas; as linhas reais ainda dependem de coordenadas e geometrias verificadas
para entrar no planejamento. Não são desenhadas retas para preencher trajetos ausentes.

Endpoints adicionais: `GET /api/catalogue/` (filtro `q`) e
`GET /api/catalogue/routes/<id>/` (sequência e metadados da variante).


## Geolocalização aproximada das paradas

A conversão usa endereços e ruas de um recorte local do OSM, com escolha de candidatos
pela ordem da variante e pelos sentidos permitidos da malha viária. Resultados estimados
são identificados no mapa; casos ambíguos ficam para revisão. Não há consulta em lote
ao Nominatim.

Com o ambiente Python ativo (`source .venv/bin/activate` ou `workon bus`):

```bash
python backend/manage.py migrate
python backend/manage.py geolocate_stops --download
```

Para repetir sem novo download, retire `--download`. Consulte o inventário completo
das importações, as fórmulas, critérios, limites e instruções de auditoria em
[Importações e geolocalização](docs/IMPORTACOES_E_GEOLOCALIZACAO.md).


Para diagnosticar apenas uma variante, use seu identificador do catálogo:

```bash
python backend/manage.py geolocate_stops --route ID_DA_VARIANTE
```

Com `--route`, a execução registra estimativas para auditoria, mas não publica coordenadas nas paradas. As ocorrências das execuções anteriores são preservadas. Estimativas geográficas continuam sujeitas à validação em campo ou por cadastro operacional.

## Relatório, mockup e entrevistas

| Local | Conteúdo |
| --- | --- |
| [docs/relatorio_parcial/](docs/relatorio_parcial/README.md) | Relatório parcial em LaTeX, referências em autor-data, glossário e apêndice técnico |
| [docs/relatorio_final/](docs/relatorio_final/README.md) | Relatório final em elaboração, discussão de Santos e avaliação comunitária pendente |
| [docs/mockup/](docs/mockup/README.md) | Apresentação conceitual em PDF e rascunho de e-mail para Osmar |
| [docs/apresentacao_avaliacao/](docs/apresentacao_avaliacao/README.md) | Apresentação genérica de oito páginas para avaliação externa e encaminhamento a profissionais |
| [docs/imagens/](docs/imagens/README.md) | Fonte única das telas, capturas, diagrama do banco e logo oficial da UNIVESP |
| [docs/entrevistas/](docs/entrevistas/) | Transcrição da entrevista e registro do retorno sobre bilhetagem |
| [docs/IMPORTACOES_E_GEOLOCALIZACAO.md](docs/IMPORTACOES_E_GEOLOCALIZACAO.md) | Fontes externas, conversão de dados, algoritmo de geolocalização e auditoria |

O título do relatório é **“Sistema de acesso a informações do transporte público por QR Code em pontos de ônibus”**. Ponto a Ponto é o nome do projeto.

As pastas `docs/relatorio_parcial/imgs`, `docs/relatorio_final/imgs` e `docs/mockup/imgs` são links simbólicos relativos para `../imagens`. Preserve esses links ao copiar o repositório. Para atualizar uma tela nos documentos, edite o arquivo em `docs/imagens/` e recompile os PDFs correspondentes. As imagens conceituais não são capturas do protótipo funcional nem demonstram validação com usuários.

### Compilar os PDFs

As dependências LaTeX são adicionais às da aplicação. Consulte a [instalação do relatório](docs/relatorio_parcial/README.md#instalação). A partir da raiz do repositório:

```bash
(cd docs/relatorio_parcial && latexmk -lualatex -interaction=nonstopmode -halt-on-error relatorio_parcial_pi2.tex)
(cd docs/mockup && latexmk -pdf -interaction=nonstopmode -halt-on-error mockup_ponto_a_ponto.tex)
```

Os PDFs são gerados ao lado dos respectivos arquivos `.tex`. PDFs e auxiliares de compilação são ignorados pelo Git; os fontes e as imagens são versionados. Para remover somente auxiliares, mantendo os PDFs:

```bash
(cd docs/relatorio_parcial && latexmk -c relatorio_parcial_pi2.tex)
(cd docs/mockup && latexmk -c mockup_ponto_a_ponto.tex)
```

### Planejamento de trocas em São Paulo

O planejamento usa rodadas de embarque sobre as sequências e calendários do GTFS. Retorna alternativas não dominadas em tempo estimado e número de trocas, dentro das próximas seis horas. A espera de serviços por frequência é estimada como metade do intervalo; `exact_times=1` usa a grade programada. Cada troca acrescenta margem mínima de dois minutos antes de buscar o próximo embarque. Datas excepcionais e horários após 24:00 são considerados. Esses valores são hipóteses de planejamento e não garantem conexões operacionais.

As baldeações exigem o mesmo identificador de parada. Caminhadas entre pontos, plataformas distintas e integrações tarifárias não são calculadas. A interface detalha linhas, sentido, embarque, desembarque e espera por trecho. O mapa recorta a geometria GTFS entre as paradas de cada trecho e desenha o ônibus em azul contínuo. Os acessos a pé entre endereços e paradas usam o roteador de pedestres e aparecem em rosa tracejado. As cores têm contraste específico no modo escuro. Se uma geometria estiver ausente, a interface informa a limitação e não inventa uma ligação reta. As previsões ao vivo não são propagadas como garantia de conexão para os trechos seguintes.

Semântica dos horários e frequências: [referência oficial GTFS Schedule](https://gtfs.org/documentation/schedule/reference/).

### Sentido das paradas e caminhada em São Paulo

As setas são tangentes ao traçado GTFS a até 35 metros da parada. Podem existir vários sentidos no mesmo ponto. Quando a geometria está ausente ou ambígua, o rumo até a próxima parada é mostrado como aproximado; no fim do itinerário, o indicador representa a chegada e pode usar a parada anterior. Se nem a sequência permite determinar um rumo, o sentido é informado como indisponível. A busca e o popup também identificam linha e destino. A sinalização do local continua sendo a referência para embarque.

`GET /api/sptrans/walk/?origin=ID&destination=ID` consulta o perfil **a pé** do OSRM público da FOSSGIS. A consulta é separada dos horários e cobre pares com distância em linha reta de até 5 km. O mapa mostra a geometria retornada; pequenos acessos até a rede (no máximo 30 m de aproximação por extremidade) são tracejados e entram no tempo estimado a 1,3 m/s. Falhas, aproximações excessivas ou falsas travessias de comprimento zero não geram uma rota em linha reta de substituição. A interface compara a caminhada com os tempos das viagens GTFS calculadas. Esta etapa oferece caminhada direta, não conexões mistas com caminhada entre paradas.

O serviço externo recebe somente as coordenadas públicas das paradas. Requer internet; utiliza cache por 24 horas, timeout de 8 segundos e limite compartilhado de uma requisição por segundo entre processos da mesma máquina (SQLite temporário). Para implantação distribuída ou maior volume, utilize roteador próprio e limitação centralizada. Atribuição e link para correções aparecem na interface, conforme a [política da FOSSGIS](https://routing.openstreetmap.de/about.html). Tempos a pé não consideram semáforos, condições atuais ou necessidades individuais de acessibilidade.

### Carregamento progressivo dos pontos do mapa

A consulta por limites visíveis aceita `batch_size` (1–200) e `offset`. Ordena as paradas pela proximidade ao centro informado e devolve `next_offset`, `total` e `revision`. O mapa pede 32 pontos inicialmente e lotes seguintes de 96; interrompe consultas anteriores quando a área muda. Não há redução do total de paradas visíveis.

O servidor mantém em memória, por processo, o cadastro e os sentidos já calculados, conservando no máximo duas versões do GTFS. A chave considera caminho, inode, tamanho e data de modificação do banco: uma nova importação invalida os dados anteriores. Consultas de lotes já calculados não executam SQL, embora o endpoint abra a conexão de leitura. Reiniciar o servidor deixa o cache frio.

O navegador reutiliza áreas completas por dois minutos (até oito áreas e 30 mil referências) e até oito mil pontos individuais para reaproveitar a parte comum entre áreas. Os lotes acrescentam marcadores sem recriar os existentes. A revisão retornada pelo servidor invalida o cache local quando detectada uma mudança do GTFS; uma área inteiramente servida pelo cache pode permanecer na revisão anterior até o prazo de dois minutos. Em instalações com vários processos, cada processo possui seu próprio cache.

### Endereços e sentido do embarque

A busca sem número identifica paradas pelo nome da rua no GTFS, normalizando abreviações e acentos. O mapa enquadra o conjunto e mantém a escolha manual. Nomes iguais geograficamente separados são distinguidos pelo resultado selecionado; lacunas ou nomes divergentes no cadastro podem impedir a identificação de todas as paradas.

Com número, a sugestão precisa conter o número solicitado; o centro da rua não é usado como se fosse o endereço exato. Com embarque conhecido, o sistema compara até 12 paradas próximas (até 500 m do endereço e no máximo 250 m além da parada mais próxima), priorizando menos trocas e depois menor distância ao endereço. A comparação usa o sentido e a ordem das paradas no GTFS, dentro da janela de serviço. Se o embarque veio de um endereço, sua parada também é reavaliada ao escolher o destino. Atravessamentos e distâncias a pé ainda precisam ser conferidos no local; a distância desta seleção é geográfica.

### Acompanhar um ônibus sem escolher destino

Na tela **Próximos ônibus**, clique na previsão **Embarque em… / Ver ônibus no mapa**.
O mapa mostra o veículo selecionado e o percurso até a parada de embarque, com
atualizações a cada 5 segundos. O enquadramento é ajustado ao abrir; atualizações
seguintes preservam o zoom e a posição escolhidos pelo passageiro. Use **Voltar aos
próximos ônibus** para retornar à lista.

Esse fluxo não exige destino nem calcula uma viagem. Se a posição ou o percurso
não puderem ser determinados, a tela informa a indisponibilidade e não substitui
o veículo escolhido por outro. Uma passagem ambígua da mesma linha pela parada
também não gera um percurso presumido.

## Localização do passageiro em São Paulo

O mapa acompanha a posição autorizada pelo navegador, com círculo de precisão. Na primeira posição disponível, centraliza no passageiro e ajusta o zoom para mostrar um raio mínimo de 250 m no menor eixo do mapa (500 m entre bordas), tanto em telas verticais quanto horizontais; as atualizações seguintes preservam o enquadramento. Cada consulta de rotas usa a posição disponível do passageiro como início da caminhada até o embarque, incluindo seu custo no tempo estimado. Sem localização, utiliza o endereço de origem ou a parada selecionada. Atualizações do GPS movem o marcador sem reiniciar a busca; atualizar horários ou iniciar uma consulta usa a posição mais recente.

Para colar as coordenadas copiadas do Maps, use `location` com o par
**latitude, longitude**, separado por vírgula. Espaços são aceitos:

```text
http://127.0.0.1:8000/?location=-23.561902423411315, -46.680757605637645
```

O navegador pode codificar os espaços e a vírgula na URL; a posição permanece a mesma.
Use ponto como separador decimal. Esse parâmetro recebe o par de coordenadas, não
um link de compartilhamento do Maps. Não misture `location` com `latitude`/`longitude`
na mesma URL. Remova o parâmetro e recarregue para voltar ao GPS.

O formato com dois parâmetros continua disponível:

```text
http://127.0.0.1:8000/?latitude=-23.5505&longitude=-46.6333
http://127.0.0.1:8000/?stop=1206717&latitude=-23.5505&longitude=-46.6333
```

`latitude` e `longitude` substituem o GPS somente nesta navegação e precisam ser
informados juntos, com ponto decimal: latitude entre −90 e 90 e longitude entre
−180 e 180. Os parâmetros são preservados durante a navegação; altere a URL e
recarregue para mudar o cenário, sem reiniciar o servidor. Um par incompleto,
vazio ou inválido apresenta erro.

Sem esses parâmetros, a aplicação usa a localização autorizada pelo navegador.
Para voltar ao GPS, remova ambos da URL e recarregue. A posição de teste é
identificada como simulada; ela não simula ônibus nem previsões da SPTrans.
Não há configuração de coordenadas pelo `.env`.

No celular, GPS requer HTTPS e permissão do navegador; HTTP pelo IP da rede permite testar coordenadas simuladas, mas não habilita o GPS. O acompanhamento termina ao sair da tela/aplicação e não armazena histórico de posições.

Com localização conhecida e sem embarque já identificado, basta selecionar o destino. O planejador busca embarques próximos à posição. A ação “Alterar embarque” permite escolher outro ponto pelo mapa, endereço ou favoritos, preservando o destino; nessa escolha explícita o GPS não substitui a origem. “Usar minha localização” restaura a origem automática. Entrada por QR Code conserva o contexto da parada.

O planejador admite até 1 km por caminhada de acesso, saída ou baldeação (13 min 20 s a 4,5 km/h), comparando o tempo total com espera e ônibus. O enquadramento inicial do mapa permanece em 250 m. Percursos a pé continuam sujeitos à verificação e aos limites de execução da busca.

## Planejador de conexões — branch `feat/busca-bidirecional`

O novo planejador usa um artefato estrutural no SQLite derivado, seleciona **16
trajetos com um ônibus, 8 com dois e 4 com três**, pela soma das distâncias de
ônibus e caminhada. Calcula o custo preliminar dos até 28 candidatos, refina os
mais promissores e transmite **até cinco alternativas** progressivamente.

A seleção por distância é uma heurística deliberada: pode excluir uma alternativa
mais rápida. Não é uma garantia de ótimo global. A implementação usa junções
indexadas pelas duas extremidades e avaliação temporal para a frente; não é um
algoritmo temporal bidirecional completo.

### Requisitos

- Ambiente Python e dependências de `requirements.txt`, conforme a instalação acima.
- GTFS importado por `import_sptrans`, com paradas, linhas, viagens, horários,
  frequências, calendários e shapes. `SPTRANS_DATABASE` identifica esse banco.
- Espaço para o GTFS e o banco derivado `<GTFS>.routing.sqlite3`. A base atual ocupa
  aproximadamente 600 MiB no índice derivado; catálogos adicionais aumentam esse
  tamanho. Reserve espaço adicional para reconstrução atômica e arquivos temporários.
- Para caminhadas entre paradas diferentes, percursos reais verificados por roteador
  de pedestres. Distância em linha reta não cria uma conexão caminhável.
- `SPTRANS_TOKEN` válido apenas para refinamento operacional. Construção e consultas
  `--offline` não precisam do token. A credencial permanece no backend.
- Histórico de circulação é opcional e deve ser fornecido com procedência. Sem ele,
  os custos usam a programação GTFS, identificada nos resultados.

### Construir o grafo e verificar caminhadas

Na raiz do projeto, com o ambiente Python ativo:

```bash
python backend/manage.py build_sptrans_graph
```

Esse comando reconstrói o banco derivado e substitui seus artefatos anteriores.
**Não o repita para apenas acrescentar pares ao catálogo.** Uma reconstrução também
exige importar/verificar novamente caminhadas e importar novamente os históricos.
O GTFS original não é alterado.

A caminhada usa **4,5 km/h**. `walk_edge` persiste separadamente distância em metros
e tempo em segundos, calculado na preparação; a consulta reutiliza ambos.

```bash
python backend/manage.py verify_sptrans_walks --origin 1211364 --limit 4
python backend/manage.py verify_sptrans_walks --file caminhadas-verificadas.jsonl
```

O JSONL aceita `origin`, `destination` e `result`, com `available`, `distance_meters`,
`geometry` (pares latitude/longitude) e `source`. A geometria, os extremos e o limite
de distância são validados. Cada sentido deve ser verificado separadamente.

O roteador público existente não deve receber milhões de solicitações em lote.
Para cobertura ampla, use um processo de roteamento próprio e importe os resultados
pelo arquivo. `pending` e `unavailable` nunca viram caminhadas utilizáveis por aproximação.

### Instalar e materializar o artefato conexões

```bash
python backend/manage.py build_sptrans_connections
python backend/manage.py build_sptrans_connections --pair 1211364 6714560
python backend/manage.py build_sptrans_connections --pairs-file docs/algoritmos/conexoes-pares.csv
```

`--pair ORIGEM DESTINO` pode ser repetido. O CSV usa as colunas `origin,destination`.
O processamento é retomável: pares completos na revisão atual são reutilizados;
`--force` os recalcula. `--database` permite escolher outro banco derivado.

O limite padrão é 60 segundos por categoria/par. `--seconds 120` aumenta-o.
Uma consulta interrompida fica explicitamente incompleta e pode ser repetida;
um subconjunto arbitrário não é apresentado como os menores trajetos. A ordenação
por distância acontece **antes** do limite 16/8/4.

| Artefato | Conteúdo |
| --- | --- |
| `connection_segments` | Segmentos entre paradas consecutivas dos padrões e distâncias projetadas no shape. |
| `connection_variants_1`, `_2`, `_3` | Visões relacionais das combinações com um, dois e três ônibus. |
| `connection_variants` | Visão consolidada das três categorias. |
| `connections` / `conexoes` | Catálogo **materializado por par**, com os menores trajetos, distâncias, tempo de caminhada e referências às arestas. |
| `connection_pairs` | Revisão, completude, quantidade e tempo de construção por categoria/par. |
| `historical_profiles` | Perfis de circulação importados, separados da estrutura. |
| `historical_days` | Exceções de tipo de dia para perfis históricos, como feriados. |
| `connection_operational_mappings` | Correspondências linha/sentido/parada validadas durante consultas operacionais, com data. |

As visões representam combinações possíveis no grafo verificado; **não há uma
materialização global de todos os pares da cidade**. Isso evitaria um produto de
centenas de milhões de pares, multiplicado pelas variantes. Os pares desejados são
preparados explicitamente por CSV. Não consulte a visão consolidada inteira sem
filtrar origem e destino.

Conexões de ônibus sem distância conhecida não participam do ranking por distância.
O catálogo referencia padrões com linha, sentido, índices de embarque/desembarque e
segmentos. Diferentes padrões não são confundidos só porque têm os mesmos extremos.

Se as caminhadas mudarem, a revisão invalida os catálogos anteriores. Execute novamente
`build_sptrans_connections --pairs-file ...`. Reimportar GTFS exige reconstruir o grafo.

### Consultar estrutura e planejamento

```bash
python backend/manage.py query_sptrans_connections 1211364 6714560 --structure
python backend/manage.py query_sptrans_connections 1211364 6714560 --offline --at 2026-10-07T08:00:00-03:00
python backend/manage.py query_sptrans_connections 1211364 6714560 --stream
```

- `--structure`: JSON com `trajetos`, `trechos`, linhas/sentidos, distâncias e caminhada.
- `--offline`: sem chamadas externas ao Olho Vivo.
- `--at`: horário ISO 8601 com fuso; **sempre offline**, para não misturar previsões atuais com uma viagem histórica.
- `--stream`: NDJSON incremental; o último registro contém `complete: true`.
- `--access-meters` / `--egress-meters`: distâncias **já verificadas** de acesso/saída;
  a ferramenta não verifica a geometria desses valores fornecidos manualmente.
- `--max-transfers`: 0, 1 ou 2.

O custo preliminar usa ônibus + caminhada + **300 segundos por baldeação**. Essa
penalidade substitui provisoriamente a espera intermediária. Na avaliação detalhada,
é removida e substituída pela espera calculada. A margem de segurança existente de
120 segundos para transferência permanece separada da caminhada e da espera.
Calendários, exceções, viagens após meia-noite e frequências são considerados.
Frequência sem fase exata mantém a hipótese identificada de meio intervalo.

Os dez primeiros candidatos são a rodada inicial, não um corte definitivo. Os demais
são avaliados ou podados. A poda só começa a limitar o TOP 5 após existirem cinco
resultados e usa o custo da **quinta** alternativa. Caminhada obrigatória e margens
restantes fornecem limites inferiores; uma estimativa histórica alta não é usada como
prova de que a alternativa perderá. Caminhos parcialmente avaliados são podados
se seu tempo acumulado mais o restante mínimo exceder o quinto colocado.

O refinamento agrupa consultas iguais de linha/sentido/parada e reutiliza o cliente
Olho Vivo existente. Previsões antigas, veículos inalcançáveis e conexões incompatíveis
não são usados como embarques válidos. As chegadas posteriores continuam estimadas
por histórico/GTFS: uma previsão de linha/veículo não identifica automaticamente a
viagem GTFS exata. Na ausência de previsão utilizável, a programação é mantida com
sua procedência. Não se promete um tempo “preciso”.

### Perfis históricos

O esquema inicial usa segmentos **entre paradas GTFS consecutivas**, não IDs de vias
OSM. Um estudo por via precisa ser associado/agregado a esses segmentos antes de
importar; não há map matching automático nem coleta de históricos nesta implementação.

CSV aceito por `--profiles`:

```text
pattern_id,segment_index,day_type,start_second,end_second,speed_kmh,source,samples,kind
```

`day_type`: `weekday`, `saturday`, `sunday` ou `holiday`. Faixas são [início,fim), em
segundos locais desde meia-noite, entre 0 e 86400. `source` e amostras positivas são
obrigatórios. Faixas sobrepostas, segmentos desconhecidos e velocidades inválidas
são rejeitados atomicamente.

```bash
python backend/manage.py build_sptrans_connections --profiles velocidades.csv
```

`kind` deve ser `running`: circulação sem o tempo de parada programada. Velocidade
comercial não deve ser importada como circulação; precisa ser decomposta antes para
não duplicar paradas. O avaliador atravessa as faixas e os dias durante o deslocamento,
e acrescenta uma única vez a permanência programada nas paradas intermediárias.
Se faltar cobertura em qualquer parte de um segmento, usa o tempo GTFS desse segmento.
O primeiro tipo de dia é definido pelo calendário civil; exceções podem ser cadastradas
em `historical_days(date,day_type)` com data ISO e tipo `holiday`, por exemplo.

Alterar perfis não invalida o catálogo de distâncias. Não foram criadas velocidades
fictícias para preencher a ausência de dados históricos.

### Usar na aplicação e comparar com o planejador anterior

Nesta branch, `SPTRANS_PLANNER=connections` é o padrão. A consulta progressiva lê a
**tabela física `conexoes` do arquivo `sptrans.materialized.sqlite3`**, usando apenas
pares com as três categorias concluídas. Os índices temporal e estrutural precisam
corresponder ao mesmo GTFS. Não há composição nem materialização de conexões durante
a requisição.

A origem pode ser uma parada, a localização do passageiro ou uma coordenada escolhida
no mapa. O planejador procura paradas próximas nas duas pontas e reutiliza o roteador
a pé da SPTrans/RAPTOR para verificar acesso ao embarque, transferências e saída até
o destino real. Cada caminhada aceita tem até 1 km pelas ruas; seu tempo é calculado
com a referência de 4,5 km/h. A caminhada final materializada é substituída pelo
percurso do desembarque até o destino real, sem duplicar distâncias. A busca só
publica trajetos com caminhadas verificadas e embarques temporalmente alcançáveis.
A verificação usa até 64 consultas de caminhada e um prazo suave de 30 segundos.

**Se a busca bidirecional não retornar rotas válidas, o PaP usa automaticamente o
planejador SPTrans/RAPTOR.** Isso inclui artefatos ausentes, desatualizados ou sem
cobertura, falta de horários compatíveis e caminhadas inviáveis. Pedidos de três
baldeações também usam RAPTOR, pois o materializado cobre até três ônibus. Quando
há alternativas válidas no modelo novo, elas são usadas sem uma segunda busca RAPTOR.

O JSON preserva o contrato de viagens/caminhadas da interface e informa `planner`
e, no fallback, `planner_fallback`. `materialization_city_complete` indica a cobertura
do artefato, que ainda é parcial; a seleção por distância não garante ótimo global.
Os bancos estáticos são abertos somente para leitura. Para usar apenas o planejador anterior:

```bash
SPTRANS_PLANNER=raptor python backend/manage.py runserver
```

Também é possível configurar `SPTRANS_PLANNER` no `.env` e reiniciar o servidor.
`SPTRANS_CONNECTION_API_BUDGET=20` limita o início de novas consultas operacionais
por busca a um orçamento suave de 20 segundos; uma chamada iniciada pode terminar
depois desse prazo, sujeita ao timeout do cliente. O token não aparece nos artefatos.

### Testes e limites de cobertura

```bash
python backend/manage.py test transit.test_sptrans_graph transit.test_sptrans_connections
python backend/manage.py test transit
```

A geração local e suas verificações estão registradas em
[validacao-conexoes.json](docs/algoritmos/validacao-conexoes.json). O arquivo identifica
os nove pares preparados, as quantidades reais e as limitações de cobertura.

Os testes cobrem ordenação antes do limite, proporções, cinco melhores, candidato
posterior aos dez primeiros, caminhada, revisão do catálogo, faixa horária/meia-noite,
paradas contadas uma vez, previsão inacessível, conexão perdida, API indisponível,
procedência, integração com a resposta da aplicação e ausência de reconstrução na consulta.

A base local ainda contém grande quantidade de caminhadas pendentes. `complete` no
catálogo significa ranking completo **no grafo verificado**, não cobertura completa
da cidade. Restrições GTFS opcionais não importadas pelo importador atual (como
`transfers.txt` e `pickup_type/drop_off_type`) permanecem uma limitação do modelo.
O ranking não garante FIFO para qualquer perfil histórico arbitrário nem ótimo global;
os históricos devem ser validados antes do uso operacional.

## Índice direto e reverso de toda a cidade

O comando abaixo percorre **cada padrão de itinerário no sentido correto** e gera
apenas pares de posições `i < j`. Não enumera o produto cartesiano das paradas da
cidade e não limita a dez itinerários nem aos nove pares do catálogo experimental.
Reutiliza as geometrias/projeções e a programação do grafo já preparado:

```bash
python backend/manage.py build_sptrans_graph          # somente se o grafo ainda não existir/estiver desatualizado
python backend/manage.py build_sptrans_direct
```

A saída padrão é `sptrans.direct.sqlite3`, ao lado do GTFS configurado em
`SPTRANS_DATABASE`. `--graph-database` seleciona o grafo de entrada; `--database`
seleciona outra saída. O novo arquivo é construído separadamente, validado e
substituído atomicamente. Uma falha preserva a saída anterior. O GTFS e o banco
`sptrans.routing.sqlite3` não são modificados por esse comando.

O arquivo contém padrões, paradas, geometrias, calendários, programação e todas as
conexões diretas disponíveis no grafo de origem. A geração **não aplica TOP 16**:
reter apenas 16 linhas antes da busca poderia eliminar uma opção útil na combinação
com outro ônibus. Os limites são aplicados nas consultas. As distâncias desconhecidas
permanecem `NULL`; não são convertidas em zero ou distância em linha reta.

| Artefato | Significado |
| --- | --- |
| `ride_edge` | Conexão real de ônibus, com origem, destino, padrão, índices no itinerário e distância. |
| `direct_out` | Índice por origem/destino, para expansão a partir do embarque. |
| `direct_in` | Índice por destino/origem, para expansão reversa a partir do destino. |
| `direct_forward` | `search_from=origin`, `search_to=destination`. |
| `direct_reverse` | `search_from=destination`, `search_to=origin`; mantém `origin`/`destination` reais do ônibus. |
| `direct_services` | Conexões com código de linha, sentido GTFS e letreiro. |
| `single_transfer` | Visão de encontros `A→B` e `B→C`, sem materializar todas as baldeações. |
| `direct_meta` | Procedência, contadores, validação e tempos de geração. |

**Busca reversa não cria um ônibus no sentido contrário.** Se existe `B→C`, a busca
reversa a partir de C encontra B, mas a viagem continua sendo de B para C. As duas
visões referenciam a mesma aresta; as geometrias não são duplicadas.

```bash
# Destinos alcançáveis saindo do ponto, com limite explícito de resultados:
python backend/manage.py query_sptrans_direct 1211364 --limit 16

# Origens que chegam ao destino no sentido real de seus ônibus:
python backend/manage.py query_sptrans_direct 6714560 --reverse --limit 16

# Mesmo par, consultado nas duas direções de busca (mesmos serviços reais):
python backend/manage.py query_sptrans_direct 1211364 6714560
python backend/manage.py query_sptrans_direct 6714560 1211364 --reverse

# Até oito combinações de dois ônibus, com encontro no mesmo ponto B:
python backend/manage.py query_sptrans_direct 1211364 6714560 --transfer --limit 8
```

`--transfer` faz a junção indexada das saídas de A com as entradas em C, exigindo que
o desembarque do primeiro trecho seja o embarque do segundo e que os padrões sejam
diferentes. Ordena pela distância total antes do limite. `--seconds` estabelece o
orçamento SQL (padrão 5 segundos); interrupções são informadas com `complete=false`.
`has_more` informa a existência de resultados além do limite.

Essas consultas são **estruturais**: `structural_only=true`. Não consultam Olho Vivo,
não garantem que os horários de dois ônibus sejam compatíveis e não incluem caminhada
entre pontos diferentes. Essa avaliação continua sendo responsabilidade do planejador
temporal. Uma distância desconhecida é preservada no índice direto/reverso, mas não
participa do ranking de distância das combinações com baldeação.

O mínimo programado a bordo não inclui espera e não é previsão operacional. A direção
GTFS não deve ser confundida com os códigos de sentido da API. A cobertura é a do GTFS
importado; viagens inválidas excluídas na preparação continuam registradas nos metadados.
Este artefato é separado do catálogo 16/8/4 e sua geração não altera a seleção da interface.

```bash
python backend/manage.py test transit.test_sptrans_direct
```

Os testes verificam a ordem das paradas, igualdade entre arestas diretas/reversas,
uso dos índices, encontro correto em B, rejeição do sentido inexistente, preservação
das variantes além de 16, distância desconhecida, calendários, reconstrução atômica
e ausência de consultas externas. A medição da geração completa está em
[validacao-diretas-cidade.json](docs/algoritmos/validacao-diretas-cidade.json).


### Conexões físicas: pré-processamento e consulta separados

A preparação tem **duas etapas distintas**. `build_sptrans_city_connections` gera
`sptrans.connections.sqlite3`, com componentes compartilhados (trechos diretos,
caminhadas e transferências). As views desse arquivo são ferramentas de construção
offline; **não são uma materialização dos trajetos finais**.

`materialize_sptrans_connections` gera `sptrans.materialized.sqlite3`. Nesse segundo
arquivo, `conexoes` é uma **tabela física**. Para cada origem/destino preparado, ela
armazena as **16 menores conexões de um ônibus, 8 de dois e 4 de três**, pela soma das
distâncias de ônibus e caminhada. São quotas sobre os trajetos completos, não sobre
os pontos intermediários. Todas as variantes fora dessas quotas não são armazenadas
como trajetos finais. Essa seleção por distância é uma heurística: pode descartar
uma viagem mais rápida quando os horários e as condições operacionais forem considerados.

Cada registro contém origem, destino, quantidade de ônibus, ordem, IDs dos trechos e
das caminhadas, distância de ônibus, distância a pé, tempo a pé e distância total.
Os índices `conexoes_distancia` e `conexoes_reversas` atendem à busca por par/categoria
nos dois sentidos, sem inverter o sentido real dos serviços. Linhas, calendários,
horários, padrões e sentidos continuam no artefato estrutural compartilhado; o leitor
recupera seus atributos por ID, sem compor trajetos ou recalcular distâncias.
A distância caminhável é preservada separadamente do tempo calculado a **4,5 km/h**.

A composição offline de três ônibus reutiliza, entre destinos consecutivos da mesma
origem, os prefixos, as ocorrências de paradas e os trechos intermediários elegíveis.
O cache fica em memória, pertence à execução e mantém apenas uma origem; mudar a
origem libera o contexto anterior. As exclusões específicas do destino, o ranking e
as quotas continuam sendo aplicados por par. Os componentes só entram no cache após
sua preparação completa; categorias interrompidas continuam pendentes. A enumeração
municipal já agrupa destinos por origem; em arquivos de pares, agrupá-los da mesma
forma permite aproveitar o reuso. O esquema dos bancos não mudou e categorias prontas
continuam sendo preservadas na retomada. Um processo já em execução só utilizará o
novo código quando for reiniciado; esta alteração não reinicia a geração automaticamente.

Requisitos: Python/Django instalado conforme este README, GTFS importado, grafo,
ligações diretas e matriz pedestre verificada. A materialização não usa token nem API
externa. Os custos a bordo, esperas, compatibilidade temporal e refinamento com Olho
Vivo são etapas posteriores; o shortlist estrutural não garante serviço no horário.

```bash
python backend/manage.py build_sptrans_direct
python backend/manage.py build_sptrans_city_connections --walk-database sptrans.walks.sqlite3

# pares.json: [["1211364", "120010332"], ...]
# Também aceita {"pairs": [{"a": "1211364", "b": "120010332"}, ...]}.
python backend/manage.py materialize_sptrans_connections --pairs-file pares.json

# Todos os destinos alcançáveis de uma origem (pode repetir --origin):
python backend/manage.py materialize_sptrans_connections --origin 1211364

# Cidade: descobre pares pelos padrões direcionados, sem produto cartesiano de todos os pontos.
# Pode demandar muito tempo/disco. A geração é retomável por par/categoria.
python backend/manage.py materialize_sptrans_connections --all --seconds 600 --min-free-gib 5

# Consulta APENAS registros prontos; não realiza composição dinâmica:
python backend/manage.py query_sptrans_city_connections 1211364 120010332
```

`--source` indica o arquivo de componentes; `--database` indica o consolidado físico.
`--seconds` pertence exclusivamente à **geração offline** e limita cada categoria.
Se ela exceder o prazo, fica `timeout`; repetir o comando retoma somente categorias
pendentes. Categorias concluídas, inclusive as que têm zero trajetos, ficam `ready`.
A consulta exige as três categorias prontas: um par pendente provoca erro explícito,
sem fallback para busca dinâmica e sem afirmar que não existem rotas. Quotas maiores
que 16/8/4 não são aceitas pela consulta.

Cada categoria é publicada numa transação, com seus trajetos e estado juntos. A
reserva de disco interrompe a geração preservando o que foi concluído. O manifesto
identifica GTFS, componentes e matriz pedestre; fontes alteradas são rejeitadas e
exigem novo artefato. A simples existência do arquivo **não significa cobertura da
cidade inteira**: `materialization_status` registra a cobertura por par/categoria e
`city_complete` só é marcado após terminar a execução `--all` sem pendências.

```sql
-- No arquivo sptrans.materialized.sqlite3:
SELECT * FROM conexoes
WHERE origin='1211364' AND destination='120010332' AND boardings=3
ORDER BY distance_meters,rank LIMIT 4;

SELECT state,COUNT(*) FROM materialization_status GROUP BY state;
```

A composição offline de três ônibus agrupa prefixos e sufixos em torno do ônibus
intermediário. A redução por grupo preserva as restrições estruturais futuras e o
TOP K; testes confrontam a seleção com a enumeração exaustiva. Nenhum custo de
composição é transferido para a consulta. A interface da aplicação continua usando
seu planejador configurado; esta etapa fornece o artefato e a consulta estrutural
para o avaliador temporal, sem trocar silenciosamente o planejador da interface.

```bash
python backend/manage.py test transit.test_sptrans_materialized transit.test_sptrans_city_connections
```

### Componentes offline: ônibus + caminhada e índice reverso

Esta seção descreve `sptrans.connections.sqlite3`, a fonte da materialização física
explicada acima. As views e exemplos SQL abaixo são para pré-processamento; a consulta
operacional usa a tabela física de `sptrans.materialized.sqlite3`.

A versão 2 do artefato municipal acrescenta caminhada **depois de cada trecho de
ônibus**, inclusive depois do último desembarque. O limite é **1.000 metros por
perna de caminhada**, calculados pela rede pedestre, incluindo os pequenos acessos
entre a coordenada da parada e a rede. O tempo é persistido como `distancia_m / 1.25`
(4,5 km/h). A soma de várias caminhadas de uma viagem pode exceder 1 km.

O gerador usa um OSRM **local com perfil foot**, não o perfil de automóvel nem o
servidor público para consultas em massa. A geometria da caminhada não é materializada
nessa matriz: a distância é calculada na rede real, e a geometria pode ser obtida no
mesmo roteador quando necessário. Não se gera uma linha reta fictícia. O artefato
registra perfil, identificação da rede, procedência OSM, distância, tempo e situação
de cada par. Paradas a mais de 20 m de uma via pedestre são marcadas `unsnappable`;
pares sem ligação, além do limite ou inválidos não entram nas conexões.

Preparação centralizada, a partir da raiz do projeto:

```bash
# Instalação completa, incluindo artefatos municipais:
./setup.sh --all --osm-pbf /caminho/sudeste.osm.pbf
# Retoma apenas a geração, com ambiente já instalado:
./setup.sh --artifacts-only
# Reconstrói todos os derivados, preservando backup:
./setup.sh --artifacts-only --rebuild-artifacts --osm-pbf /caminho/sudeste.osm.pbf
```

O Makefile é interno ao setup. Seus alvos executam verificações de compatibilidade
mesmo quando os arquivos existem; só os geradores necessários são executados.
Versões dos geradores devem ser incrementadas quando o formato/semântica dos dados
mudar. Ao trocar o extrato OSM, use `--rebuild-artifacts`: a compatibilidade atual
não detecta automaticamente outro PBF informado se a matriz já estiver válida.
Os tempos dos geradores executados ficam em `.cache/setup/artifacts-*.json`.
A materialização incompleta retorna erro e pode ser retomada sem declarar a cidade
inteira concluída. A reconstrução não reimporta o GTFS; para isso use `--refresh-gtfs --routes`.
Os comandos Django descritos nas seções técnicas são ferramentas internas de diagnóstico;
o fluxo normal de instalação/geração é sempre `setup.sh`.

O recorte preserva as vias completas e seus nós referenciados, incluindo tags de
barreiras, com margem de aproximadamente 2,5 km em torno da extensão das paradas.
A configuração local utiliza o perfil foot incluído no OSRM 6.0.0; pode diferir do
perfil específico usado pelo servidor público FOSSGIS da aplicação. A duração no
artefato é sempre recalculada a 4,5 km/h, independentemente da velocidade interna
utilizada pelo perfil para escolher percursos. Dados © contribuidores do
[OpenStreetMap](https://www.openstreetmap.org/copyright), extrato da
[Geofabrik](https://download.geofabrik.de/south-america/brazil/sudeste.html).

`sptrans.walks.sqlite3` é separado do grafo anterior e processa os pares espacialmente
candidatos já enumerados, sem produto cartesiano entre todas as paradas. Uma falha do
roteador aborta a geração e preserva o arquivo anterior. O consolidado reconhece esse
arquivo automaticamente quando ele existe; `--walk-database` permite escolher outro.
Sem arquivo pedestre, usa somente as caminhadas verificadas existentes no grafo.

| Estrutura | Função |
|---|---|
| `walking_link`, índices `walking_out`/`walking_in` | Distâncias dirigidas verificadas até 1 km. |
| `bus_walk_exit` | Liga cada ocorrência de desembarque aos percursos pedestres disponíveis. |
| `bus_walk_forward` | Ônibus A→B seguido de caminhada B→C, com distâncias separadas e tempo a pé. |
| `bus_walk_reverse` | Consulta a partir de C para encontrar A; conserva os sentidos reais A→B→C. |
| `one_bus` | União dos trechos de um ônibus com e sem caminhada final. |
| `conexoes_1`, `conexoes_2`, `conexoes_3`, `conexoes` | Composições com caminhada nas trocas e/ou no destino final. |

A exclusão é contextual: a caminhada B→C após embarcar em A só entra se C **não**
for alcançável permanecendo no mesmo padrão/sentido de ônibus a partir daquele
embarque. Não se exclui C apenas porque outra linha o atende. Uma ocorrência de C
anterior ao embarque não constitui atendimento direto. A regra também se aplica
às caminhadas intermediárias. Por decisão de escopo, essa exclusão pode eliminar
caminhadas que seriam mais rápidas que continuar no ônibus; isso precisa ser
considerado ao avaliar qualidade temporal.

```sql
SELECT * FROM bus_walk_forward WHERE search_from='1211364' AND search_to='120010332';
SELECT * FROM bus_walk_reverse WHERE search_from='120010332' AND search_to='1211364';
SELECT * FROM conexoes_3 WHERE origin='1211364' AND destination='120010332'
ORDER BY distance_meters,edge1,edge2,edge3,final_walk LIMIT 4;
```

A representação continua compartilhada: trocas e saídas para caminhada são
materializadas; as combinações completas são expandidas por par nas visões SQL.
As quotas 16/8/4 e o limite de consulta permanecem explícitos. Não há garantia de
melhor viagem temporal pelo ranking de distância, e o artefato não acrescenta
caminhada antes do primeiro ônibus. A ampliação atual diz respeito aos artefatos;
a interface e o avaliador temporal anterior não passam a consumi-los automaticamente.

```bash
python backend/manage.py test transit.test_sptrans_city_connections transit.test_sptrans_walk_artifacts
```


Na consulta de três ônibus, o gerador de candidatos combina as extremidades direta
e reversa em ordem de um limite inferior: distância do primeiro ônibus mais a do
último ônibus e sua caminhada final. Os custos intermediários são não negativos.
A busca só encerra quando esse limite supera a quarta melhor conexão completa já
encontrada. Os encontros intermediários usam o índice `transfer_meet`; o teste compara
o resultado com a enumeração SQL completa em um grafo pequeno, incluindo caminhadas
e empates. O orçamento de execução continua sendo informado por `complete`.

A geração municipal com a base OSM local verificou **952.608** ligações pedestres de
até 1 km, representadas em `sptrans.walks.sqlite3`. O consolidado contém **4.267.783**
saídas de desembarque para caminhada e **22.769.860** possibilidades de transferência
compartilhadas, sujeitas às exclusões contextuais da consulta. Esses números não são
uma contagem de viagens completas materializadas. As medições e verificações estão em
[validacao-conexoes-caminhada-cidade.json](docs/algoritmos/validacao-conexoes-caminhada-cidade.json).

### Parâmetros do planejador e dos artefatos

Os padrões `PAP_*` estão documentados no `.env.example`. Caminhadas usam
`PAP_WALK_LIMIT_METERS` (1000 m por ligação), `PAP_WALK_SPEED_KMH` (4,5 km/h),
`PAP_WALK_SNAP_METERS` (20 m por extremidade) e `PAP_OSM_MARGIN_DEGREES`.
O tempo é persistido como distância / (velocidade / 3,6). O limite por ligação
não limita a caminhada total de uma viagem com várias conexões.

As quotas são `PAP_ROUTES_DIRECT`, `PAP_ROUTES_TWO_BUSES` e
`PAP_ROUTES_THREE_BUSES` (16/8/4). `PAP_TRANSFER_SECONDS` é uma margem
de transferência, diferente de `PAP_INTERMEDIATE_WAIT_SECONDS`, usada na
classificação preliminar. Horizonte, refinamento e alternativas finais também
estão no exemplo. Valores inválidos interrompem a inicialização com o nome
da configuração; valores secretos não são impressos.

`PAP_OSRM_*` controla versão, compilação, threads, matriz e inicialização;
`PAP_WALK_WORKERS`, `PAP_WALK_BATCH_SIZE` e `PAP_WALK_REQUEST_SECONDS`
controlam as consultas locais. O lote mais a origem deve caber na matriz.
`PAP_OSM_PBF_URL` define a fonte padrão; `--osm-pbf` seleciona um arquivo local.

`PAP_ROUTE_SECONDS` e `PAP_MIN_FREE_GIB` fornecem os padrões do setup.
Os argumentos `--route-seconds` e `--min-free-gib` têm prioridade. O prazo
é por par/categoria, não pela materialização municipal inteira.

Após mudar configurações, reinicie os processos e execute
`./setup.sh --artifacts-only`. As assinaturas verificam limite, velocidade,
snap, margem OSM, versão OSRM e quotas, regenerando as etapas afetadas.
Artefatos antigos sem a assinatura de caminhadas são reconstruídos uma vez.
A materialização incompatível é preservada com sufixo `.obsolete-*`.
Ajustes de paralelismo e timeout não invalidam resultados já concluídos.


### Experimento: cobertura antes de três ônibus e convergência geográfica

O comando abaixo compara o modo padrão com duas heurísticas, sem modificar bancos,
sem usar Olho Vivo e sem ativar a política na aplicação ou no `setup.sh`:

```bash
python backend/manage.py compare_sptrans_heuristics --pairs-file pares.json \
  --at 2026-10-08T08:00:00-03:00 --seconds 60 > comparacao-heuristicas.json
```

`pares.json` contém uma lista de pares de identificadores, como `[["A", "B"]]`.
`--source` seleciona os componentes e `--graph` o índice temporal compatível.
O modo experimental só explora três ônibus quando não existe conexão estrutural
original com um ou dois. Em cada sequência de linha, a partir do embarque, examina
a parada central (a anterior das duas centrais) e a última das paradas restantes.
Poda quando ambas se afastam estritamente do destino em distância geográfica;
empates e coordenadas ausentes preservam a exploração. Isso pode descartar uma
aproximação em outra parada e uma conexão necessária. Não é prova de ausência de rota.

O JSON distingue exclusão por política, timeout, candidatos perdidos, conectividade,
tempo estrutural e melhor duração programada no mesmo instante GTFS. A caminhada
inicial não é expandida; caminhadas intermediárias e finais preparadas são consideradas.
Os modos alternam ordem, mas os caches do sistema operacional não são reiniciados.
A comparação é exploratória, sem estimar p95/p99. O reuso por origem não é usado
nessa comparação pareada; os prefixos filtrados dependem do destino e não podem ser
compartilhados indiscriminadamente. Resultados não substituem a materialização municipal.

Para materializar a cidade com essa política, pelo ponto de entrada de instalação:

```bash
./setup.sh --artifacts-only --route-heuristics
```

O resultado fica em `sptrans.materialized.heuristics.sqlite3`, separado de
`sptrans.materialized.sqlite3`. A assinatura registra `coverage_then_midpoint_last_v1`;
não é permitido retomar um banco com outra política. A tabela `policy_decisions`
registra exclusões de três ônibus e contagens das sequências examinadas/podadas.
Uma categoria concluída pode estar vazia por decisão da política, não por ausência
física de conexão. A retomada preserva categorias concluídas e tenta novamente os
timeouts. A conclusão municipal significa cobertura do escopo dessa política.
O novo arquivo não substitui automaticamente o banco usado pela aplicação.

### Ambiente da aplicação

Defina `PAP_ENVIRONMENT=production` (padrão) ou `PAP_ENVIRONMENT=development` no `.env` da raiz. Em produção, a marca do RAPTOR e a medição de distâncias pelo botão direito ficam desativadas. Essas ferramentas estão disponíveis apenas em desenvolvimento. Após alterar, execute `npm --prefix frontend run build`; se estiver usando o Vite, reinicie o servidor de desenvolvimento. A variável não altera o `DEBUG` do Django.

## Participação voluntária na pesquisa

O passageiro pode contribuir com a pesquisa ou usar o transporte sem gravação. A decisão pode ser alterada em **Configurações → Participação na pesquisa**. Feedback continua disponível sem participar. Consulte [comportamento, retenção e testes](docs/CONSENTIMENTO_PESQUISA.md).
