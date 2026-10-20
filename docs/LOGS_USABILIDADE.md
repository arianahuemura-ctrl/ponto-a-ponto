# Registro de pesquisa — v2

A aplicação só monta após clicar em Concordo e continuar no aviso inicial. Não há controle flutuante; fechar o site encerra a participação. O aviso reaparece a cada carregamento, antes da captura. A sessão não é vinculada a cadastro, mas os dados NÃO são anônimos.

Contrato: GET /api/usability/ retorna token assinado e CSRF. POST conserva eventos existentes e aceita trace {payload: string JSON} até 12000 caracteres; lotes de até 20 eventos e 256 KiB. trace inclui categoria, UTC do dispositivo, tempo monotônico e dados. Conteúdos maiores são fragmentados com id/index/total/text. O exportador local mantém esses fragmentos para remontagem por id e index.

Após aceite: estados, buscas, coordenadas, favoritos, rota escolhida, respostas das consultas instrumentadas, cliques, campos da interface, rolagem e viewport do mapa. Não registra cookies, credenciais ou cabeçalhos. Não é vídeo nem replay visual exato: operações não instrumentadas, mapas externos e perdas de rede podem impedir reconstrução completa.

Fila em memória de até 5000 eventos, envios em lotes pequenos e repetição de falhas temporárias. Fechamento abrupto ou indisponibilidade prolongada pode perder eventos. Limite 3000 eventos/minuto/sessão. Armazenamento separado em ~/.local/state/pap/usability/events.sqlite3, arquivo 0600; retenção de 30 dias com limpeza na próxima gravação e teto global de 50000 eventos. Sem endpoint de leitura pública.

Consulta: python3 scripts/usability_logs.py; exportação: python3 scripts/usability_logs.py --session UUID. Ordene por seq. Preserve exportações de pesquisa em local restrito.

## Comparação visual (research-v3)
Após novo aceite, rrweb 2.1.7 captura DOM/CSS, inputs, ponteiro (50 ms), scroll (100 ms) e canvas a até 5 fps/WebP qualidade 0.8. O aviso descreve a reprodução visual. Senhas e elementos data-private são bloqueados. Não captura outras abas, microfone ou câmera. Recursos externos podem não ser incorporados (CORS); o player pode precisar carregar imagens do mapa. Não é captura pixel a pixel garantida. rrweb usa iframe com execução habilitada para canvas: exportações devem permanecer locais e só devem ser abertas de sessões confiáveis. O player bloqueia conexões de API via CSP.

Exportar uma sessão e medir os mesmos dados em variantes:

```
python3 scripts/export_replay.py --session UUID --output /caminho/privado/sessao
```

Abra replay.html. Contém controles de pausa, busca temporal e velocidade. Cada camada é exportada em JSON e gzip: basico; diagnostico (inclui básico); visual; completo (diagnóstico + visual). comparacao.json também indica bytes de payload SQLite, sequências ausentes e fragmentos incompletos. Não atribui páginas/índices SQLite a sessões. Sessões anteriores não ganham replay retroativamente.

Captura continua limitada à fila em memória e à retenção já descritas. Eventos visuais disputam o limite de 3000 eventos/minuto e 50000 registros globais; se excedidos, a reconstrução pode ficar incompleta. Não apague camadas antes de avaliar lacunas. A comparação de gzip é por arquivo e não representa o tamanho atual do banco, que não foi alterado para compressão.

## Feedback
Botão Feedback disponível após o aceite. Formulário com categoria e mensagem (1 a 2000 caracteres), sem exigir identificação. POST /api/usability/ envia evento feedback {payload: JSON com category, message, at e elapsed} pelo token da sessão e CSRF. Envio direto com confirmação do servidor, independente da fila de replay; repetição usa o mesmo seq para deduplicar. Sucesso apenas após HTTP 200. A administração exibe o feedback na sessão, com link para o instante registrado. Segue a mesma retenção dos demais eventos.


## Proteções de ingestão (19/10/2026)
Contrato: lotes inválidos retornam 400; limites temporários retornam 429; capacidade esgotada retorna 503. Nenhuma dessas recusas remove sessões por lotação. A expiração após 30 dias continua ativa. Limites globais, compartilhados entre sessões, são verificados na mesma transação SQLite da gravação: 12000 eventos/minuto, 32 MiB de payload/minuto, 50000 eventos e 256 MiB de payload armazenado. As configurações PAP_TELEMETRY_EVENTS_PER_MINUTE, PAP_TELEMETRY_BYTES_PER_MINUTE, PAP_TELEMETRY_MAX_EVENTS e PAP_TELEMETRY_MAX_BYTES permitem ajuste. Bytes medem payload UTF-8, não todo o arquivo SQLite. O limite individual de 3000 eventos/minuto permanece.

Traces exigem kind e details objeto; eventos visuais exigem tipo, timestamp finito e data objeto. Fragmentos têm índice/total validados, até 2048 partes de 8000 caracteres. A reconstrução descarta registros inválidos e informa suas sequências na lista de problemas; não altera o original. Isso valida o envelope, não garante autenticidade da navegação nem valida toda a gramática interna do rrweb.

A capacidade global protege retenção, mas um cliente abusivo ainda pode ocupar a cota e interromper novas capturas. Para pesquisa restrita, adotar convites temporários; limitar na borda com cuidado com redes compartilhadas. Não há identificação confiável por IP neste túnel, e cabeçalhos de IP arbitrários não são usados para confiar em clientes.

A instância pública envia X-Frame-Options DENY e CSP com frame-ancestors none, object-src none e base-uri self. Uma política mais restritiva é enviada em Report-Only para observar incompatibilidades no console antes de ativá-la. Não há coletor de relatórios CSP configurado. Administração/replay local mantém sua política própria e suporte ao iframe de mesma origem.
