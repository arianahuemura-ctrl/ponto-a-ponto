# Estado do worktree acadêmico — 2 de novembro de 2026

Branch `relatorio`; HEAD `e5077b9c12b89c099f900cad0911f7498dafb06d`. Revisão editorial concluída; commits e push autorizados pelo responsável em 02/11/2026. Trabalho acadêmico restrito a este worktree; aplicativo e vídeo não foram alterados nesta etapa.

## Entrega atual

- [PDF editorial](relatorio_final/PaP_relatorio_2026-11-02_revisao_editorial.pdf): **167 páginas**, **24998553 bytes**. MD5 `5bdbc062a2680394ea8d4f97d715caef`; SHA-256 `b24c37067fc84c389d21a79f97cef1eabc00d6921791bb6d7ad08a69e36b9e55`.
- [Detalhes e conformidade](relatorio_final/revisao-editorial-2026-11-02/REVISAO_EDITORIAL.md), [validação](relatorio_final/revisao-editorial-2026-11-02/VALIDACAO.json), [patch próprio desta etapa](relatorio_final/revisao-editorial-2026-11-02/alteracoes-editoriais.patch).
- Fonte ativa: `docs/relatorio_final/relatorio_final_pi2_v2.tex`; compilar LuaLaTeX/latexmk com **`-norc` e diretório novo**, evitando o exportador histórico. Otimização posterior pikepdf sem perdas; scripts na auditoria.
- Referência anterior [168 páginas](relatorio_final/PaP_relatorio_2026-11-02_revisao_tecnico_cientifica.pdf), MD5 `64f0e94138166eb508b648910fbe960f`, preservada. O ZIP da revisão técnico-científica corresponde àquela versão anterior.

## Alterações editoriais e decisões

- Seção 2.3: 19→17 páginas; 3.1: 15→14; Apêndice C: 9→8. E.2: dez páginas mantidas por seus detalhes de reprodução. Texto principal 69→66 páginas. Listas acrescentam três páginas; saldo total 168→167.
- Apenas a figura complementar da lista extensa do Olho Vivo deixou de ser reproduzida; original e hipótese mantidos. Capturas de viagem completa e último trecho reunidas, praticamente com a mesma escala. Repetições funcionais/arquiteturais condensadas com remissões.
- Apêndices A–H e Anexo A integral mantidos. Material do grupo permanece nos apêndices; documento externo no anexo. Parecer assinado, capturas, gráficos, resultados e referências preservados.
- Metadados Title/Author/Subject/Keywords preenchidos; oito autores, título e data documental idênticos no fonte. Listas previstas no modelo institucional incluídas; abstract/keywords em inglês dependem de confirmação institucional, pois o modelo fornecido não os prevê, embora constem na estrutura geral da NBR 14724:2024.
- Mantidas distinções entre programação, simulação e operação; 99,666% é a cobertura estrutural anterior à ARTESP. Nenhum benefício com passageiros foi acrescentado. Dados ARTESP 337 paradas, 16 linhas/variantes e 705/427/359 viagens; benchmark de 1.637 sucessos pareados preservado. Parecer de outubro não abrange novembro.

## Verificações

- LuaLaTeX final: código 0, `compile-04.log`; `validate.py`: código 0, `validate-02.log`. Zero referências ausentes/Overfull/caracteres ausentes; 13 Underfull e três avisos de compatibilidade preexistentes, sem corte observado.
- 167 páginas renderizadas, zero páginas vazias, paginação contínua da Introdução ao final; 119 entradas de listas/sumário, 64 marcadores e 458 links internos conferidos. 84 URIs externas preservadas, disponibilidade HTTP não reavaliada.
- Otimização sem perdas comprovada por igualdade de pixels a 144 dpi em todas as páginas, texto/links/metadados/marcadores. Seis páginas externas idênticas à referência fora do cabeçalho de numeração. Manifesto de 1.189 arquivos anteriores preservado, exceto dois fontes editoriais e README. Capturas e documento assinado intactos por SHA-256.
- Logs e cópias anteriores: `.cache/setup/editorial-20261102/`. Referência mais antiga inclui alterações locais preexistentes em `refs/auditoria/relatorio-20261102-original-tecnico-cientifica`; não confundir seu diff com esta revisão. `git diff --check` aprovado. Nenhum teste da aplicação, medição, importação ou materialização executado.

## Próximos passos

Usar o PDF editorial como referência de nova revisão. Confirmar exigência institucional de abstract/keywords e link definitivo do vídeo na capa; não afirmar homologação institucional nem impressão verificada. Protocolo físico de QR e avaliação com passageiros seguem pendentes. Preservar trabalho local e histórico; novos commits dependem de autorização. Não alterar dados, sessões Codex ou configurações globais.

## Publicação autorizada em 02/11/2026

Entrega editorial, fontes ativos, gráficos e capturas necessários à compilação, auditorias da revisão e integração ARTESP selecionados para commit e push na branch `relatorio`. O PDF anterior de 168 páginas e seu pacote também são preservados no versionamento. Logs/builds de `.cache/setup/` passam a ser ignorados; acervos brutos e auditorias históricas não selecionadas permanecem no disco, sem exclusão. O aplicativo segue na branch própria. Conferidos hashes da entrega e `git diff --check`; não houve nova edição do conteúdo do relatório nesta publicação. Referência anterior `e5077b9`; consultar `git log` para os commits da publicação. A consulta do remoto usou referências temporárias isoladas por causa de uma referência interna inválida `refs/codex/.../base`, preservada sem alteração.
