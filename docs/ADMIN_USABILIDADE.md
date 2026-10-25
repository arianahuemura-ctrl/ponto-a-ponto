# Administração de usabilidade

Acesso em /admin/usability/ (lista paginada de sessões) e /admin/usability/<UUID>/ (detalhes, dispositivo, eventos e replay). Requer usuário Django ativo com is_staff. Use o login existente /admin/login/. Nenhuma credencial padrão é criada. As rotas ficam indisponíveis na instância pública, inclusive com autenticação, pelo bloqueio de /admin/. Sem mudanças no banco da aplicação.

Todas as leituras de telemetria são locais, SQLite em modo read-only, com respostas no-store. O player e seus assets são servidos por HTTP autenticado na mesma origem. Metadados v1 incluem userAgent, idioma(s), plataforma informada, dimensões de tela/viewport, pixel ratio, touch points e fuso; não inferem modelo físico exato, identidade ou localização por IP. Sessões anteriores mostram apenas campos disponíveis. Player não é vídeo MP4: é reconstrução rrweb, com canvas limitado a 5 fps e dependência de algumas imagens externas. Lacunas e fragmentos ausentes são exibidos; não se garante integridade além dos registros recebidos.


A coluna Ações oferece Apagar, Exportar JSON e Exportar vídeo. Apagar abre uma página de confirmação e exige POST com CSRF; remove os eventos da sessão (incluindo feedback e replay) apenas do banco de telemetria. Uma sessão ainda ativa pode enviar novos eventos após a exclusão. Exporte antes se precisar preservar os registros.

Exportar JSON baixa os registros da sessão e os eventos reconstruídos, incluindo indicação de problemas encontrados. Trate o arquivo como dado de pesquisa restrito.

Exportar vídeo inicia automaticamente uma tarefa no servidor e baixa o WebM ao terminar, sem compartilhamento de tela. Mantenha a página de exportação aberta. A renderização usa Node, Playwright/Chromium instalados no frontend e processa os eventos sem aguardar o tempo real (limite: uma hora). Quadros são amostrados em mudanças registradas, com resolução temporal de 200 ms, compatível com os 5 fps da captura de canvas. Quadros visualmente idênticos são reutilizados; ffmpeg monta WebM VP9 com duração variável, preservando os intervalos ociosos. Também requer ffmpeg com libvpx-vp9. Animações CSS intermediárias não registradas não são recriadas quadro a quadro; a fidelidade depende dos eventos capturados e do carregamento das imagens. Só uma geração é executada por processo administrativo; outras recebem uma mensagem para tentar depois. O arquivo temporário é privado, restrito ao administrador que iniciou a tarefa e à sessão correspondente; arquivos concluídos são mantidos para reutilização. Reiniciar o servidor perde apenas o acompanhamento de tarefas em execução. Este gerenciador em memória destina-se ao admin local com um único processo; não usar múltiplos workers administrativos sem uma fila compartilhada. Nenhuma chamada à API é feita pelo renderizador; apenas imagens HTTPS de tile.openstreetmap.org podem ser carregadas externamente. Imagens indisponíveis e lacunas da captura afetam o resultado. Não há áudio.


Novos registros usam blocos comprimidos com zlib e compartilhados por hash dentro de cada sessão. O conteúdo é reconstruído integralmente antes de alimentar o replay ou exportar JSON: horários, eventos e respostas permanecem iguais. A API mantém o mesmo contrato; limites de ingestão e capacidade continuam calculados em bytes originais para evitar abuso de compressão. O armazenamento antigo em texto continua legível e não é convertido automaticamente. A exclusão e a expiração de uma sessão também removem seus blocos; blocos de sessões parcialmente expiradas permanecem até o último evento expirar. A coluna de tamanho inclui referências e blocos comprimidos, sem páginas/índices SQLite. Liberar registros não reduz necessariamente o arquivo SQLite no disco, pois suas páginas podem ser reutilizadas.

Validação em cópia temporária da sessão de 597 segundos: 11.289 registros reconstruídos de forma idêntica, de 29.943.218 para 13.735.071 bytes de conteúdo e referências (54,1% de redução, sem contar índices/páginas). A economia depende da repetição dos dados. Não há descarte automático de eventos durante inatividade.


As ações da lista usam ícones com dicas e nomes acessíveis. Durante a exportação, o botão mostra uma ampulheta e fica desabilitado até o download estar pronto. JSON e WebM gerados ficam em `exports/<sessão>/` ao lado do banco de telemetria, em diretório privado. O cache usa uma assinatura de todos os registros: a mesma versão é reutilizada, inclusive após reinício; novos registros geram outra versão. Excluir a sessão pela administração remove seus arquivos de exportação. Esses arquivos ocupam espaço adicional e não são contabilizados na coluna de tamanho dos eventos.


## Feedback independente e solicitações de pesquisa

Com o consentimento voluntário, novos relatos são armazenados separadamente da telemetria. Acesse `/admin/research/` pelo link na lista de sessões: o painel apresenta os 200 registros mais recentes e permite marcar uma mensagem como analisada ou excluí-la, com confirmação. O acesso exige usuário administrativo e permanece bloqueado na instância pública.

Relatos enviados com gravação ativa também aparecem no detalhe da sessão, posicionados pelo instante de recebimento do servidor. Sem pesquisa ativa, o relato não cria sessão nem replay e aparece apenas no painel de mensagens. Registros históricos de feedback continuam legíveis no replay.

**Excluir uma sessão de telemetria não exclui as novas mensagens do banco separado.** No tratamento de uma solicitação, conferir também mensagens relacionadas, exportações e cópias baixadas. Marcar como analisada não executa exclusão. O exportador JSON existente contém os eventos de telemetria; as novas mensagens independentes devem ser consultadas no painel próprio.

O contato configurado é `25202874@aluno.univesp.br`, substituível por `PAP_RESEARCH_CONTACT`. As decisões e limitações de retenção estão documentadas em [Consentimento voluntário de pesquisa](CONSENTIMENTO_PESQUISA.md).
