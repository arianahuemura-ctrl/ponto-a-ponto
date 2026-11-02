# Validação da revisão — 2 de novembro de 2026

PDF: `../PaP_relatorio_2026-11-02_revisao_tecnico_cientifica.pdf`. SHA-256: `2d2a3840bd717aa01b9ee9aa4b0a88883fc0adf9af8caf68b15e2f8b1ac0ff2d`. 168 páginas A4, 27.556.752 bytes. Fontes Times New Roman incorporadas; gráficos vetoriais. Fonte principal: `../relatorio_final_pi2_v2.tex`.

## Compilação

Executado no diretório `docs/relatorio_final`:

```sh
TEXMFCACHE=/tmp/pap-revisao-relatorio-20261102/texcache TEXMFVAR=/tmp/pap-revisao-relatorio-20261102/texcache latexmk -norc -lualatex -interaction=nonstopmode -halt-on-error -outdir=/tmp/pap-revisao-relatorio-20261102/build relatorio_final_pi2_v2.tex
```

Última compilação: `compile-08.log`, código 0. O `-norc` evita o hook histórico que exporta/remove PDFs antigos. Cache de fontes temporário, sem configuração global. As duas primeiras tentativas falharam por cache de fontes sem permissão; recompilação com cache temporário e acesso autorizado concluiu. Os logs foram preservados, inclusive os de falha.

Logs completos: `.cache/setup/revisao-relatorio-20261102-9irg257p/`, no worktree `relatorio`; log final do LuaLaTeX, `.fls`, `.aux`, `.toc` e contatos visuais também nesse diretório.

## Verificações

- `python3 validate.py`: código 0; 27 fontes TeX ativos, 95 rótulos, nenhuma referência ausente/duplicada; 54 chaves citadas e 54 entradas, nenhuma citação ausente. Entradas bibliográficas idênticas às originais, exceto ordem.
- PDF com 40 figuras e 21 tabelas numeradas; sumário e numeração conferidos. Resumo de 214 palavras e cinco palavras-chave.
- Zero `Overfull`; 13 `Underfull` de composição de parágrafos/células, examinados visualmente sem cortes. Três avisos de compatibilidade preexistente (`brazil`, `settocpreprocessor`, `addtodef`); não impedem compilação. Nenhuma referência/citação indefinida.
- PDF completo inspecionado visualmente: contato de todas as páginas, revisão de capturas, mapas, tabelas, diagramas e seis páginas do parecer. Na última passagem, páginas 1–90 foram comparadas por hash de renderização com a passagem anterior: somente 3–5 mudaram, e foram reinspecionadas; páginas 91–168 e diagrama GTFS ampliado foram vistos na compilação final. Contatos finais em `.cache/setup/revisao-relatorio-20261102-9irg257p/inspecao-visual/`.
- `pdftotext`, `pdfinfo`, `pdffonts` e renderização por `pdftoppm`: concluídos. Comparação anterior/revisado em `ALTERACOES.md`.
- 780 arquivos preexistentes conferidos por SHA-256: nenhuma ausência; mudanças somente nos nove fontes TeX editoriais listados em `validacao-automatica.json`. O README também foi atualizado, fora desse manifesto. Nenhuma captura, CSV/JSON/GeoJSON, DOCX ou documento assinado do manifesto mudou. PDF anterior intacto.
- Índice Git original intacto, HEAD `e5077b9` e branch `relatorio` preservados. Nenhum commit, merge, limpeza ou alteração do aplicativo executados nesta tarefa.
- Insumos das novas figuras reconferidos por hash. 337 identificadores de parada distintos; malha IBGE exatamente igual à da auditoria; três estações separadas; 705/427/359 viagens nos dias de referência.
- Recálculo a partir dos 3.264 registros individuais: 1.637 sucessos pareados, mediana 0,282 → 0,599 s, P95 5,698 → 5,143 s, máximo 10,712 → 5,936 s; 431 diferenças negativas e 1.206 positivas. `metricas-recalculadas.json` guarda precisão, estratos, caminhos e hashes.

## Limites

Não houve novo benchmark, teste do aplicativo, importação, materialização, coleta com passageiros, consulta operacional ou inspeção física. As execuções históricas citadas continuam identificadas por data/versão. Não foi refeito hash do banco de 88 GiB; ele não foi aberto por esta revisão. Resolução das capturas originais limita a leitura de detalhes muito pequenos; ampliações não recuperam informação ausente. Não foi realizada impressão física A4 ou homologação institucional. Pendências externas em `ALTERACOES.md`.

Os fontes de compilação incluem imagens e PDF assinado necessários. O acervo histórico completo permanece no repositório e na referência Git, não é duplicado integralmente no pacote. Para regerar estatísticas, o CSV original do benchmark continua no worktree da aplicação, com caminho e hash no manifesto; a compilação usa os gráficos vetoriais já incluídos.

## Verificação do pacote de fontes

O ZIP foi extraído em diretório temporário novo; todos os arquivos conferiram com `MANIFESTO.json`. O mesmo comando LuaLaTeX foi executado a partir dos fontes extraídos, com saída em `/tmp/pap-revisao-relatorio-20261102/build-pacote`: código 0, 168 páginas, texto e paginação extraídos idênticos ao PDF entregue; nenhuma referência indefinida ou Overfull. Log `compile-pacote.log` no diretório de logs acima. `git diff refs/auditoria/relatorio-20261102-original-tecnico-cientifica --check -- docs/relatorio_final`: código 0, sem erros de espaços. Links locais atuais de README e CODEX_STATE verificados.

O patch editorial foi produzido comparando cada arquivo físico com a árvore original, incluindo fontes novos. Isso evita interpretar arquivos preexistentes ainda não rastreados pelo índice como exclusões no diff Git. Nenhum arquivo foi excluído; a conferência de integridade é a evidência desse fato.
