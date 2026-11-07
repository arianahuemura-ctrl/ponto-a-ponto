# Acesso público temporário — PaP

Esta configuração adiciona um processo Gunicorn em `127.0.0.1:8001`. Não reinicia nem reconfigura o desenvolvimento em `8000`, não executa migrações e não instala serviços. O túnel precisa apontar para **8001**, nunca para 8000.

## Preparação

Na raiz do projeto:

```bash
~/.virtualenvs/bus/bin/python -m pip install -r requirements-public.txt
# Somente se o frontend ainda não estiver compilado ou precisar ser atualizado:
npm --prefix frontend run build
./scripts/start_public.sh
```

O script utiliza `~/.virtualenvs/bus/bin/python`; `PAP_PUBLIC_PYTHON` permite escolher outro virtualenv. Dependências normais do projeto devem estar instaladas. WhiteNoise serve somente `frontend/dist/assets` em `/assets/`, inclusive com `DEBUG=False`; não é necessário executar `collectstatic`. A página inicial continua sendo servida pela view Django existente. Um rebuild também atualiza os arquivos usados pelo desenvolvimento; não é executado automaticamente pelos scripts. Após rebuild, reinicie apenas a instância pública para reindexar os assets do WhiteNoise.

Sem `PAP_PUBLIC_HOST`, o script procura um contêiner Cloudflare ativo apontando para `127.0.0.1:8001` ou `localhost:8001` e identifica o domínio nos logs da execução atual. Sem túnel detectado, preserva o domínio de uma instância ativa; em uma primeira inicialização, aceita somente hosts locais. Teste:

```bash
curl http://127.0.0.1:8001/api/health/
```

## Chave e isolamento

A cada início, o script gera com `secrets.token_urlsafe(64)` uma chave exclusiva e passa `PAP_PUBLIC_SECRET_KEY` pelo ambiente ao Gunicorn. Não imprime nem grava a chave. Opcionalmente, forneça essa variável por um gerenciador de segredos; não a coloque em arquivo versionado ou literal no histórico do terminal. A chave de desenvolvimento não é reutilizada. Reiniciar invalida cookies da instância temporária.

Settings públicos fixam `DEBUG=False`, independentemente do `.env`. O `.env` existente continua fornecendo as credenciais dos provedores no servidor; não é servido nem reescrito. Nenhum arquivo do projeto precisa conter o segredo público.

PID, lock, logs e temporários ficam em `~/.cache/pap-public/<identificador-do-projeto>/`, com diretório 0700 e arquivos privados. O stop valida a identidade do processo antes de sinalizar o master. Não usa `pkill`, não mata processos pela porta nem toca o servidor 8000. Uma porta 8001 ocupada causa recusa de início.

A base Django abre com URI SQLite `mode=ro`. Sessões usam cookies assinados, sem escrita em SQLite. O fluxo atual `connections` lê os artefatos existentes e usa tabelas temporárias para correspondências operacionais; o fallback calcula em memória. O controle temporário de requisições pedestres usa uma base nova em TMPDIR privado. Não há cópia, importação, migração, remoção ou alteração intencional de bases existentes. Simulação histórica pressupõe sua configuração já existente; se faltar, a instância pública não a criará.

## Quick Tunnel (endereço temporário)

Requer o executável `cloudflared`, obtido pelo método oficial adequado ao ambiente. Os scripts não o instalam nem criam serviço. Em um terminal separado:

```bash
cloudflared tunnel --url http://127.0.0.1:8001
```

Copie o domínio `...trycloudflare.com` exibido. Enquanto ele não estiver permitido, o Django responderá 400 às solicitações desse domínio. Em outro terminal, configure **o domínio exato**:

```bash
./scripts/stop_public.sh
PAP_PUBLIC_HOST='SEU-DOMINIO.trycloudflare.com' ./scripts/start_public.sh
```

Substitua o exemplo pela URL real sem `https://`, porta ou caminho. Não use `*` nem `.trycloudflare.com`. O processo `cloudflared` pode permanecer aberto durante esse reinício. Nenhum acesso é liberado automaticamente para outros domínios. O QR Code passa a gerar URLs HTTPS do domínio configurado.

Teste a página, busca, alternativas, acompanhamento e GPS em um celular por dados móveis. HTTPS permite solicitar geolocalização, mas a permissão ainda depende do navegador. O domínio muda ao criar outro Quick Tunnel: execute novamente `./scripts/start_public.sh`. O script detecta o novo domínio e reinicia somente o Gunicorn público, se necessário.

Para interromper o acesso, use **Ctrl+C no terminal do cloudflared**. Para encerrar também a instância pública:

```bash
./scripts/stop_public.sh
```

A porta 8000 permanece ativa. Não há serviço de inicialização automática.

Quick Tunnels são destinados a testes, têm limites de concorrência e não suportam SSE. O PaP utiliza **NDJSON (`application/x-ndjson`) via fetch**, não SSE. A entrega incremental deve ser validada pela URL real: proxy, buffering e limites de duração podem mudar o comportamento. Não se deve considerar o teste local como validação do túnel. Para apresentação com disponibilidade previsível e controle de acesso, prefira túnel nomeado e Cloudflare Access, em configuração separada e autorizada.

## HTTPS e confiança no proxy

Gunicorn escuta somente no loopback. `forwarded_allow_ips` limita a confiança a `127.0.0.1,::1` e aceita como indicador HTTPS apenas `X-Forwarded-Proto: https`. Ele converte o cabeçalho validado para `wsgi.url_scheme`; Django mantém `SECURE_PROXY_SSL_HEADER=None` e não confia diretamente no cabeçalho nem em `X-Forwarded-Host`.

O domínio público acessado por HTTP é redirecionado para HTTPS; HTTP local continua funcionando para diagnóstico. Cookies públicos têm nomes próprios e atributo Secure. Não há HSTS persistente para o domínio temporário. Esse modelo pressupõe cloudflared na mesma máquina e processos locais confiáveis; não exponha 8001 em `0.0.0.0` nem use proxy remoto sem revisar a cadeia de confiança. Não configure reescrita de Host no túnel.

## Contrato e revisão da API

| Recurso | Instância pública |
|---|---|
| `/` e `/assets/...` | React e arquivos compilados; Host validado antes dos assets |
| `/api/health/`, `/api/location-config/` | GET preservado; coordenadas simuladas vêm da própria consulta |
| `/api/sptrans/stop-catalogue/`, `stops/`, `addresses/`, `destination/` | Consultas públicas preservadas |
| `/api/sptrans/board/`, `trips/<id>/`, `walk/`, `qr/<id>/` | Contratos de consulta preservados, incluindo NDJSON |
| APIs históricas de consulta e catálogo | GET preservado; dados devem continuar identificados como históricos/simulados |
| `/admin`, `/admin/...`, `/api/demo/evaluation/`, `/explorar/` | 404, somente na instância pública |
| Métodos diferentes de GET/HEAD | 405, exceto POST validado em `/api/usability/`; caminhos bloqueados continuam 404 |
| Host não permitido | 400, inclusive arquivos estáticos |
| Falha 5xx da API | Mensagem genérica, sem traceback na resposta |
| `.env`, bancos, arquivos do repositório | Não há rota de arquivos para esses recursos |

Riscos identificados e limites:

- As consultas não têm autenticação: qualquer pessoa com a URL pode consultar os dados. Admin e gravação de avaliações ficam indisponíveis; isso não transforma a URL em acesso privado.
- Planejamento, geocodificação e consultas operacionais consomem CPU, memória e cotas externas. Um worker com quatro threads limita execução simultânea, mas não é proteção completa contra abuso. A instância compartilha hardware com o desenvolvimento. Use janela curta e público limitado; para restrição de participantes, configure Cloudflare Access em túnel nomeado.
- O catálogo histórico inclui URLs de origem, metadados de coleta e evidências de geolocalização. São dados de procedência, mas exigem revisão antes de circulação ampla. Não há endpoint de leitura das avaliações pessoais existentes. O endpoint que aceitava inserir avaliações foi removido nesta instância.
- Respostas de planejamento podem conter diagnósticos de indisponibilidade de artefatos. Na instância pública, esses diagnósticos são substituídos por mensagem genérica; os cálculos e alternativas não são alterados.
- Endereços e coordenadas são enviados aos provedores usados pela aplicação. O log de acesso público omite query strings e IP; logs de erro permanecem privados e podem conter informações internas. Revise-os antes de compartilhar. Cloudflare pode registrar seus próprios dados de tráfego.
- Favoritos permanecem no navegador de cada origem. Os favoritos do endereço localhost não são automaticamente transferidos para o domínio do túnel.
- Consultas reais dependem de GTFS, artefatos, credenciais e disponibilidade dos provedores. Sucesso HTTP não comprova precisão operacional.
- `/api/health/` mantém o contrato histórico e não atesta funcionamento da SPTrans; valide também pontos, itinerários e rotas.

## Validação local

```bash
PAP_PUBLIC_SECRET_KEY="$(~/.virtualenvs/bus/bin/python -c 'import secrets; print(secrets.token_urlsafe(64))')" \
  ~/.virtualenvs/bus/bin/python backend/manage.py test mbm.test_public --settings=mbm.public_settings
```

Os testes não criam bancos: verificam configuração, bloqueios, Host, assets, erros e contrato de streaming. Para dados reais, consultar pontos, embarque, itinerário e planejamento em 8001. Verificar 8000 antes/depois, parar 8001 e confirmar que somente o processo público terminou. Conferir ausência de segredos no diff antes de versionar.

Referências oficiais:
- https://whitenoise.readthedocs.io/en/stable/django.html
- https://gunicorn.org/reference/settings/
- https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/

## Verificação realizada em 19/10/2026

- Sete testes de contrato passaram, sem criação de banco de testes.
- Todos os nove assets compilados (JS, CSS, PNG e SVG) retornaram 200 no Gunicorn.
- Consultas reais de pontos, embarque e itinerário retornaram 200. O itinerário consultado tinha 48 paradas e 644 pontos de geometria; a consulta de rota retornou uma alternativa.
- Chromium com viewport de 390×844 renderizou o React e o painel Próximos ônibus sem erro JavaScript.
- Domínio de teste explícito validado localmente com Host e X-Forwarded-Proto; QR gerou URL HTTPS. Host diferente foi rejeitado. X-Forwarded-Ssl não foi aceito como indicador HTTPS.
- Admin, avaliação e caminhos de arquivos privados retornaram 404. Métodos de escrita retornaram 405 nos endpoints de consulta.
- Parada da instância pública fechou 8001 e manteve 8000 respondendo 200. Reinício e início repetido foram verificados.
- Estado final: 8000 preservada; 8001 ativa e aceitando apenas hosts locais. Nenhum túnel iniciado, pois cloudflared não foi encontrado. Entrega incremental pelo Cloudflare e acesso real por celular na internet continuam dependendo do teste com o domínio real.

Registro opcional de eventos por sessão: [Logs de usabilidade](LOGS_USABILIDADE.md). A escrita ocorre apenas na base separada descrita nesse documento.

## Atualização automática do domínio

Com o túnel Docker já iniciado, execute apenas:

```bash
./scripts/start_public.sh
```

O script reutiliza o túnel existente; não cria nem encerra contêineres. Consulta apenas contêineres ativos da imagem `cloudflare/cloudflared` direcionados explicitamente à porta 8001. Usa os logs desde a inicialização atual. Se houver mais de um domínio candidato, exige escolha explícita; se a URL ainda não estiver nos logs, pede nova tentativa. `PAP_PUBLIC_HOST` explícito tem prioridade. Para cloudflared fora do Docker, continue informando essa variável.

A troca mantém o bloqueio entre operações e verifica a identidade do processo antes da parada. A porta 8000 não é modificada. Não acompanha mudanças continuamente: depois de recriar o túnel, execute o start novamente.

Testes sem Docker/rede reais: `python scripts/test_public_instance.py`.
