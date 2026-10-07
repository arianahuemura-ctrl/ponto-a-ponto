# Ponto a Ponto (PaP)

**Deslocamento facilitado entre origem e destino.**

Protótipo acadêmico do Projeto Integrador em Computação II da UNIVESP, iniciado com o contexto do transporte público de Mauá e com navegação integrada ao cadastro GTFS de São Paulo. O QR Code identifica a parada física e inicia a consulta no navegador, sem exigir instalação de aplicativo ou conhecimento prévio do nome do ponto ou da linha. O passageiro pode consultar as linhas, escolher um destino e comparar viagens. Utiliza **Django/Python**, **React/Vite** e **Leaflet**, com dados geográficos do OpenStreetMap.

O cadastro de paradas, linhas, variantes e documentos públicos é importado de `fonts/` para `db.sqlite3`. O cenário demonstrativo usa linhas, horários e veículos **simulados**, controlados pela administração e identificados separadamente das fontes reais. Os trajetos destacam as ruas do OSM; ainda não são itinerários validados pela operadora.

## São Paulo: navegação e destino da sessão

A página inicial abre São Paulo. O cenário anterior de Mauá continua em `/?city=maua` e nos QR Codes antigos.

1. Configure `SPTRANS_TOKEN` no `.env` da raiz. O Django lê essa chave no início; reinicie o servidor após substituí-la. A chave não é enviada ao navegador. Teste o acesso com `python backend/manage.py check_sptrans`.
2. Ative o ambiente Python e execute `python backend/manage.py import_sptrans`. O comando indexa `fonts/sptrans_gtfs/` em `sptrans.sqlite3`, separado do banco da demonstração. Repita ao substituir o GTFS.
3. Compile com `npm --prefix frontend run build` e inicie o servidor normalmente.
4. Acesse `/sao-paulo/`: a primeira etapa é **Selecionar local de embarque**. Toque em uma parada para abrir a lista de próximos ônibus; nessa janela também é possível salvar o embarque nos favoritos.
5. Toque em **Selecionar destino** para voltar ao mapa e escolher outra parada ou um favorito. A lista passa a mostrar apenas os ônibus da rota calculada, na ordem dos embarques, incluindo até duas trocas. **Alterar destino**, **Cancelar seleção** e **Cancelar viagem** permitem retomar ou encerrar o planejamento.
6. A lupa busca o endereço da etapa atual (embarque ou destino). Após três caracteres, oferece sugestões de ruas e lugares com bairro e município quando disponíveis. Sem número, selecione a rua para enquadrar suas paradas no mapa e escolher uma delas. Com número antes ou depois do nome da rua, confirme a parada sugerida. A distância exibida até o endereço é em linha reta.

O autocomplete utiliza Photon/Komoot sobre dados OpenStreetMap, com espera de 500 ms após digitar, cancelamento de consultas anteriores e cache de 10 minutos no servidor. O texto pesquisado é enviado a esse provedor externo. Quando o bairro não consta nos dados, a interface informa isso. O serviço público pode ficar indisponível; a seleção pelo mapa continua disponível.

A origem e o destino corrente ficam em `sessionStorage`, restritos à sessão da aba. Favoritos ficam em `localStorage`. **Cancelar viagem** limpa a sessão, preservando os favoritos. Um QR Code define a origem e mantém o destino se aberto na mesma sessão.

Enquanto a lista está aberta, as previsões são atualizadas a cada 30 segundos. Sem previsão, o aplicativo identifica os dados do GTFS como programação ou estimativa, sem apresentá-los como chegadas ao vivo. O cálculo respeita calendário, exceções, sentido e sequência das paradas. A rota escolhida considera tempos estimados do GTFS; as previsões atuais de uma parada de troca devem ser conferidas novamente ao chegar.

As correspondências com o Olho Vivo exigem código completo da linha e terminal de destino compatíveis. Paradas precisam pertencer à linha e ter correspondência única a até 15 metros (ou o mesmo código nessa área). Não se presume que os identificadores do GTFS sejam os mesmos da API. Quando a correspondência é ambígua ou a API não cobre uma parada, não há previsão em tempo real. Posições com mais de 3 minutos e previsões com posição capturada há mais de 5 minutos são descartadas. Em terminais, o painel limita a consulta ao vivo a 12 linhas e interrompe novas consultas após 8 segundos. Linhas não consultadas ficam identificadas na lista.

**Situação da credencial verificada em 06/10/2026:** o servidor da SPTrans respondeu, mas a autenticação com a chave local retornou `false`. O cadastro e a navegação GTFS funcionam; a exibição ao vivo depende de uma chave aceita pela SPTrans. A integração possui testes com respostas controladas, que não comprovam disponibilidade operacional.

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
| [frontend/package-lock.json](frontend/package-lock.json) | Bibliotecas JavaScript com `npm ci` |

### 2. Instalar os pacotes APT

Os exemplos consideram que o repositório foi clonado na pasta `ponto-a-ponto`. No terminal, a partir do diretório que contém essa pasta, execute:

~~~bash
cd ponto-a-ponto
~~~

Instale a lista de pacotes, removendo comentários e linhas vazias:

~~~bash
sudo apt-get update
sed 's/#.*//; /^[[:space:]]*$/d' requirements.system | xargs -r sudo apt-get install --
~~~

Se preferir **aptitude**, substitua somente o último comando:

~~~bash
sed 's/#.*//; /^[[:space:]]*$/d' requirements.system | xargs -r sudo aptitude install --
~~~

A lista inclui Python, suporte a ambientes virtuais, Git, curl, certificados HTTPS e suporte a arquivos XZ. O `pip` é fornecido dentro do ambiente virtual; não é necessário instalar as bibliotecas Python globalmente.

**Node.js é instalado no próximo passo.** O repositório APT consultado neste Ubuntu oferece Node.js 22, enquanto o projeto exige 24. Instalar apenas `nodejs` e `npm` pelo APT não atende à versão configurada neste projeto. Em outras versões de Debian/Ubuntu, confira também se `python3 --version` atende ao mínimo de 3.12.

### 3. Instalar Node.js 24

Se já usa `nvm`, pule sua instalação. Caso contrário, execute o instalador do [projeto oficial nvm](https://github.com/nvm-sh/nvm#installing-and-updating):

~~~bash
curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.8/install.sh -o /tmp/pap-install-nvm.sh
bash /tmp/pap-install-nvm.sh
~~~

Abra um novo terminal para carregar o `nvm` e volte à raiz do projeto. Então execute:

~~~bash
nvm install
nvm use
node --version
npm --version
~~~

Na raiz, `nvm install` e `nvm use` leem a versão de [.nvmrc](.nvmrc). O comando `node --version` deve mostrar `v24.x.x`.

### 4. Preparar o ambiente Python

Use o `venv`, fornecido pelo Python. Na raiz do projeto:

~~~bash
python3 -m venv .venv
source .venv/bin/activate
python --version
python -m pip install -r requirements.txt
~~~

Se `.venv` já existe, basta ativá-lo antes de instalar as dependências. Nos próximos terminais, execute `source .venv/bin/activate` na raiz do projeto.

<details>
<summary>Opção pessoal: virtualenvwrapper</summary>

O virtualenvwrapper é opcional e não faz parte dos requisitos do projeto. Se você prefere gerenciar seus ambientes com ele, pode usá-lo no lugar do fluxo acima.

Caso ainda não esteja instalado:

~~~bash
sudo apt-get install virtualenvwrapper
~~~

Carregue-o no terminal:

~~~bash
source /usr/share/virtualenvwrapper/virtualenvwrapper.sh
~~~

Para carregá-lo automaticamente, adicione essa linha ao `~/.zshrc` (Zsh) ou ao `~/.bashrc` (Bash).

Se o ambiente `bus` já existe:

~~~bash
workon bus
~~~

Caso contrário, crie-o; a criação também o ativa:

~~~bash
mkvirtualenv -p python3 bus
~~~

Com o ambiente ativo, instale as dependências na raiz do projeto:

~~~bash
python -m pip install -r requirements.txt
~~~

Nos demais comandos deste README, use `workon bus` no lugar de `source .venv/bin/activate`. Não é necessário criar os dois ambientes.

</details>

### 5. Preparar o banco e o administrador

Com o ambiente Python ativo e na raiz do projeto:

~~~bash
python backend/manage.py migrate
python backend/manage.py import_sources --download --demo
python backend/manage.py createsuperuser
~~~

A migração cria/atualiza as tabelas SQLite. A importação coleta as fontes públicas, grava o catálogo e inclui o cenário simulado (`--demo`). A coleta inicial pode levar alguns minutos. O último comando solicita nome de usuário, e-mail e senha para acesso administrativo. Se já possui um administrador, não precisa criá-lo novamente.

**Não existe usuário ou senha padrão.**

### 6. Instalar e compilar o frontend

Na raiz, com Node.js 24 ativo:

~~~bash
nvm use
cd frontend
npm ci
npm run build
cd ..
~~~

O build é salvo em `frontend/dist/` e servido pelo Django. Depois de alterar o frontend, execute novamente `npm run build` nesse diretório.

## Iniciar a aplicação

Na raiz, com as dependências instaladas:

~~~bash
source .venv/bin/activate
python start_server.py
~~~

| Acesso | Endereço |
| --- | --- |
| São Paulo — passageiro | http://127.0.0.1:8000/sao-paulo/ |
| Demonstração de Mauá | http://127.0.0.1:8000/?city=maua |
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

As variáveis são lidas do ambiente do processo; o projeto não carrega arquivos `.env` automaticamente.

| Variável | Uso |
| --- | --- |
| `DJANGO_DEBUG` | `1` para desenvolvimento; `0` para desativar DEBUG |
| `DJANGO_SECRET_KEY` | Chave própria, obrigatória com DEBUG desativado |
| `DJANGO_ALLOWED_HOSTS` | Hosts aceitos, separados por vírgulas |
| `PUBLIC_BASE_URL` | URL da aplicação gravada nos QR Codes |
| `OSM_USER_AGENT` | Identificação e contato nas consultas externas |
| `MBM_DATABASE` | Caminho alternativo para o SQLite |

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

## Localização do passageiro em São Paulo

O mapa acompanha a posição autorizada pelo navegador, com círculo de precisão. Na primeira posição disponível, centraliza no passageiro e ajusta o zoom para mostrar um raio mínimo de 250 m no menor eixo do mapa (500 m entre bordas), tanto em telas verticais quanto horizontais; as atualizações seguintes preservam o enquadramento. Cada consulta de rotas usa a posição disponível do passageiro como início da caminhada até o embarque, incluindo seu custo no tempo estimado. Sem localização, utiliza o endereço de origem ou a parada selecionada. Atualizações do GPS movem o marcador sem reiniciar a busca; atualizar horários ou iniciar uma consulta usa a posição mais recente.

Para simular um local, preencha no `.env` da raiz `SIMULATED_LATITUDE=-23.5505` e `SIMULATED_LONGITUDE=-46.6333`. Reinicie o Django e recarregue a página. As duas coordenadas substituem o GPS e a posição é identificada como simulada; deixe ambas vazias para usar o aparelho. Valores incompletos ou fora dos limites são rejeitados. Somente essa configuração pública é exposta, nunca o token SPTrans.

No celular, GPS requer HTTPS e permissão do navegador; HTTP pelo IP da rede permite testar coordenadas simuladas, mas não habilita o GPS. O acompanhamento termina ao sair da tela/aplicação e não armazena histórico de posições.

Com localização conhecida e sem embarque já identificado, basta selecionar o destino. O planejador busca embarques próximos à posição. A ação “Alterar embarque” permite escolher outro ponto pelo mapa, endereço ou favoritos, preservando o destino; nessa escolha explícita o GPS não substitui a origem. “Usar minha localização” restaura a origem automática. Entrada por QR Code conserva o contexto da parada.

O planejador admite até 1 km por caminhada de acesso, saída ou baldeação (15 minutos a 4 km/h), comparando o tempo total com espera e ônibus. O enquadramento inicial do mapa permanece em 250 m. Percursos a pé continuam sujeitos à verificação e aos limites de execução da busca.
