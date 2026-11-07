# Preparação da análise de navegação
A auditoria foi estática, no código identificado em `auditoria/versoes.json`. Nenhum banco de pesquisa, replay, mensagem ou exportação real foi aberto. O campo de comentário “sem texto livre” no cabeçalho de usability.py não é uma garantia: traces e feedback podem guardar textos/locais.

## Formato existente e relógios
`events(session,seq,received,type,data)`; primary key session/seq. `data` pode estar comprimido em blocos. O backend aceita session_start, state, action, api, error, dimmer, trace e feedback legado. Trace contém kind/at/elapsed/details, ou chunks com id/index/total/text. A exportação administrativa oferece records brutos e events reconstruídos, mais problemas de reconstrução. Não executar o exportador nesta tarefa.
received é recebimento de lote, não instante de interação. elapsed=performance.now() vale só durante a vida da página; at é relógio de parede sujeito a ajuste. seq pode persistir com sessionStorage enquanto elapsed reinicia. Lacunas podem refletir fila limitada, interrupção, limite de eventos, consentimento ou falha no envio. Não interpolar eventos que faltam.
A ausência de request_id e de marcador de planejamento enviado limita associação de respostas concorrentes. Estado journey é preenchido automaticamente pela primeira alternativa; ele não prova seleção humana. Um erro técnico não comprova dificuldade percebida. Veja `indicadores_telemetria.csv` para todos os marcos.

## Extração futura autorizada
1. Registrar autorização expressa, finalidade, abrangência e consentimento compatível. Copiar somente exportações autorizadas para área restrita com hash e acesso mínimo; não consultar bancos de produção pelo script de análise.
2. Reconstruir chunks somente se completos, na ordem de índices; conservar lacunas e conflitos. Usar versão do reconstruidor registrada. Não publicar payloads, coordenadas, busca, favoritos ou mensagens. O script legado de auditoria abre capturas e não é atalho de autorização.
3. Um analista autorizado produz JSONL normalizado conforme `schemas/evento_normalizado.json`. Mapear sessão para S001 etc., página para epoch; OD e rotas para aliases aleatórios do lote. Guardar chave separada apenas se necessária. Código de sessão não é código de pessoa. Não incluir user-agent completo; dispositivo é classe ampla.
4. Os tipos normalizados representam a classificação do analista, não novos eventos instrumentados. Anotar referência de evidência restrita e distinção entre ação explícita e estado automático fora da tabela pública. Ausência de marco recebe null, não 0.

## Segmentação reproduzível
Agrupar por alias de sessão e época de página; ordenar por seq dentro de cada época, sem reordenar épocas pelo relógio de parede. Duplicata idêntica é ignorada; conflito, salto de seq, retrocesso de elapsed ou chunk incompleto gera ressalva. Abrir tentativa quando há contexto OD, planejamento identificado ou resposta sem início conservado (truncada). Mudar OD encerra a tentativa anterior por reconfiguração, não erro. Atualizações de horário/mesmo par permanecem na tentativa; nova consulta explícita ao mesmo par pode abrir outra se comprovada.
Selecionar/detalhar não fecha necessariamente a tentativa: a pessoa pode explorar alternativas. Cancelamento só encerra como confirmado com evidência; clique de cancelar é apenas intenção. Interrupção, fim do registro e lacuna de inatividade encerram como `fim_observacao`/`lacuna`, nunca abandono. Regra de inatividade proposta: 120 s; verificar sensibilidade com 60 e 300 s em análise futura, sem escolher o limiar conforme o efeito desejado.
Sem associação segura, API fica marcada ambígua e não fornece tempos confiáveis por tentativa. Script fornece segmentação inicial para revisão humana, não rotula sucesso/dificuldade automaticamente.

## Quatro níveis de afirmação
1. Evento observado: há ação ou estado registrado.
2. Comportamento reconstruído: sequência compatível com consulta/troca; indicar lacunas.
3. Hipótese de dificuldade: interpretação ainda não corroborada.
4. Problema confirmado: erro verificável contra tarefa definida ou relato autorizado corroborado. Registrar quem confirmou e evidência, sem inventar intenção.
Múltiplas rotas podem ser exploração deliberada da avaliação. Sessões, tentativas e participantes são denominadores distintos.

## Relatório agregado
Só tipos de transição, categorias de dispositivo e intervalos amplos; excluir aliases/horários precisos e locais. Não contar pessoas únicas. Células abaixo de 3 sessões e complementos inferíveis não serão publicados. `segmentar.py` gera tentativa pseudonimizada de acesso restrito; a divulgação deve usar revisão de agregação, nunca copiar esse arquivo ao relatório. O consentimento, retenção e exclusão de `privacidade.md` precedem qualquer abertura de dados reais.

### Ferramentas de apoio
segmentar.py aceita exclusivamente o JSONL minimizado, com referência explícita de autorização. Planejamento explícito logo após contexto OD compõe a mesma tentativa; uma nova consulta comprovada após resposta abre outra. Não extrai novas ações de payloads automaticamente. agregar_telemetria.py recebe apenas a saída já autorizada e gera contagens gerais, sem aliases, locais ou datas; exige pelo menos três sessões contribuintes e suprime células/complementos pequenos. O resultado ainda exige revisão humana contra divulgação por cruzamento com outras tabelas. As contagens de tentativa não são contagens de pessoas.
