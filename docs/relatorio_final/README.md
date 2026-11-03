# Vídeo definitivo — 3 de novembro de 2026

Entrega atual: [PDF com URL definitiva](PaP_relatorio_2026-11-03_video_definitivo.pdf), **167 páginas**, **30158763 bytes**.
Vídeo: https://www.youtube.com/watch?v=rSvuIWx8QAg

Atualizada somente a capa; retirados indicação de versão provisória e aviso
pendente. Páginas 2–167 preservadas por texto e pixels. [Validação e limites](video-definitivo-2026-11-03/ATUALIZACAO.md).
MD5 `f7c3cedb7bb9d613c9819a77e16fe5cf`; SHA-256 `b3f141273264f7a2b198b50300972d704c15494bc47485de1d959fd5d9b0a488`. Atualização incluída na publicação Git autorizada em 03/11/2026; consultar o histórico da branch `relatorio`.

---

# Capturas atualizadas — 2 de novembro de 2026

Entrega anterior: [PDF com 17 capturas atualizadas](PaP_relatorio_2026-11-02_capturas_atualizadas.pdf), **167 páginas**, 28.877.638 bytes. Interface real do aplicativo `78e3935`; mapas coloridos, nomes ferroviários completos, favoritos, controles e avaliação por estrelas. Legendas e exemplos ajustados aos estados observados, incluindo a busca parcial para Guaiaúna.

[Registro da atualização](atualizacao-capturas-2026-11-02/ATUALIZACAO.md), [validação](atualizacao-capturas-2026-11-02/VALIDACAO.json) e [correspondência das capturas](atualizacao-capturas-2026-11-02/substituicoes.json). Preservados arquivos anteriores, estudos históricos, consulta ARTESP e parecer integral. Fonte ativa e comando LuaLaTeX abaixo permanecem válidos. Esta atualização está sem commit.

MD5: `b253dea82eb68d251fee52a4fae225cf`. SHA-256: `7a93bb8d7e2820a72a261e435585b8ee75403e82a8556181e4d272a18f3bd77d`.

---

# Revisão editorial — 2 de novembro de 2026

Entrega editorial anterior: [PDF revisado](PaP_relatorio_2026-11-02_revisao_editorial.pdf), **167 páginas**, 24998553 bytes. [Relatório da revisão](revisao-editorial-2026-11-02/REVISAO_EDITORIAL.md), [validação](revisao-editorial-2026-11-02/VALIDACAO.json) e [patch](revisao-editorial-2026-11-02/alteracoes-editoriais.patch).

Fonte ativa: `relatorio_final_pi2_v2.tex`. Preservados Apêndices A–H, Anexo A integral, dados, capturas originais, oito autores e data documental. Listas de figuras/tabelas e metadados acrescentados; abstract depende de confirmação institucional. O PDF anterior de 168 páginas e seu ZIP continuam abaixo como referência histórica; esse ZIP não contém a revisão editorial atual.

MD5: `5bdbc062a2680394ea8d4f97d715caef`. SHA-256: `b24c37067fc84c389d21a79f97cef1eabc00d6921791bb6d7ad08a69e36b9e55`.

Compilar com LuaLaTeX/`latexmk -norc` em diretório novo, conforme instruções abaixo. Para reproduzir a otimização, ver `revisao-editorial-2026-11-02/optimize.py`; a versão compilada também é válida e preserva o conteúdo. Não executar o hook histórico de exportação. Sem commit automático.

---

# Revisão técnico-científica — 2 de novembro de 2026

PDF revisado: [PaP_relatorio_2026-11-02_revisao_tecnico_cientifica.pdf](PaP_relatorio_2026-11-02_revisao_tecnico_cientifica.pdf), 168 páginas. Fontes: [ZIP](PaP_relatorio_2026-11-02_fontes_revisao_tecnico_cientifica.zip).

Fonte ativa: `relatorio_final_pi2_v2.tex`. A revisão editorial e sua validação estão em `revisao-tecnico-cientifica-2026-11-02/`. Veja `AUDITORIA.md`, `ALTERACOES.md` e `VALIDACAO.md` nesse diretório para escopo, evidências, resultados e pendências.

Referência Git original (inclui alterações locais): `refs/auditoria/relatorio-20261102-original-tecnico-cientifica`. É uma referência a árvore, sem novo commit. Exemplo de consulta: `git show refs/auditoria/relatorio-20261102-original-tecnico-cientifica:docs/relatorio_final/relatorio_final_pi2_v2.tex`.

Compilar o fonte ativo com LuaLaTeX em **diretório novo**, evitando o hook histórico de exportação automática:

```sh
latexmk -norc -lualatex -interaction=nonstopmode -halt-on-error -outdir=/tmp/pap-relatorio-build-NOVO relatorio_final_pi2_v2.tex
```

As referências de entrega e os comandos abaixo são registros históricos; não substituem a identificação da revisão acima. O link definitivo foi atualizado em 03/11/2026; ver entrega acima.

---

# Revisão de apresentação e legibilidade — 2 de novembro de 2026

PDF atual: [PaP_relatorio_2026-11-02_ARTESP_revisado.pdf](PaP_relatorio_2026-11-02_ARTESP_revisado.pdf), 155 páginas.
MD5: `65f4ca925b0e719c1101e6e18a584492`.

Feedback de legibilidade ferroviária documentado, com capturas reais dos temas claro e escuro e distinção entre verificação técnica e avaliação com passageiros. A ampliação ARTESP já documentada foi preservada. Vídeo atualizado na entrega `entrega-2026-11-02-artesp-revisado`; fonte, validação e versões anteriores preservadas. Link público definitivo continua pendente; não houve publicação ou commit.

Auditoria: [auditoria-apresentacao-artesp-2026-11-02](auditoria-apresentacao-artesp-2026-11-02/).

---

# Ampliação ARTESP em Mauá — 2 de novembro de 2026

PDF atual: [PaP_relatorio_2026-11-02_ARTESP.pdf](PaP_relatorio_2026-11-02_ARTESP.pdf), 154 páginas.
MD5: `e5066437612956ffc0eda173dace0f40`.

Confirmadas no GTFS original 337 paradas, 16 linhas ou variantes e 705/427/359
viagens programadas distintas em dia útil/sábado/domingo. Ao fim de semana,
324 paradas constam na programação. Capuava, Mauá e Guapituba são adicionais.
Foram examinadas 14 consultas temporais e preservada uma captura real da
interface pública com ônibus 157 e CPTM L10; seu aviso de busca parcial foi mantido.

Resumo, Metodologia, Resultados, Tabela 5, Considerações Finais e apêndice de
integração atualizados; ajuste pontual da delimitação para distinguir os três
estágios. Fontes, respostas, capturas, validação e hashes:
[auditoria-artesp-maua-2026-11-02](auditoria-artesp-maua-2026-11-02/).
O vídeo não foi modificado; avaliação e plano de substituição visual em
[video-avaliacao.txt](auditoria-artesp-maua-2026-11-02/video-avaliacao.txt).
Versões anteriores preservadas. Nenhum commit automático.

---

# Revisão corretiva de 1 de novembro de 2026

PDF revisado: `PaP_relatorio_2026-11-01_revisado.pdf`, 145 páginas, 9,875,597 bytes, MD5 `87bdf923c09bafb6c5f60ed81c284738`. Compilação LuaLaTeX/latexmk concluída.

Fontes e evidências da revisão: `revisao-consistencia-2026-11-01/`. Original de referência (MD5 fcf136604ea3aa13ea58bd884cc628b1) preservado. Foram corrigidos resumo, resultados, universo de paradas, recorte da tabela de latências e consulta concorrente; acrescentadas evidências visuais reais e rastreabilidade com lacunas explícitas. O protocolo A/B/C permanece proposto. A capa aguarda confirmação do endereço definitivo do vídeo.

O histórico abaixo mantém as datas de suas versões. Metrô e trens estão implementados no planejamento atual; previsão ferroviária ao vivo, integração tarifária e validação operacional permanecem pendentes.

---

# Atualização de 1 de novembro de 2026

Fonte vigente: `relatorio_final_pi2_v2.tex`. Nova seção B.1 e tabela 9: cobertura, integração ferroviária, publicação concorrente e desempenho por baldeação. PDF de envio conferido: `relatorio_final_pi2_v2_envio.pdf` (9.809.687 bytes). Original sem recompressão preservado. Evidências em `atualizacao-2026-11-01/`.

---

# Relatório final — Projeto Integrador II

Revisão de 7 de outubro de 2026. Versão da aplicação documentada: 4992027, branch sptrans. O modelo da facilitadora está em Modelo_Relatorio_Final.docx; o relatório parcial foi preservado em ../relatorio_parcial/.

## Conteúdo atual

O relatório reúne fundamentação de IHC, aplicação das disciplinas, metodologia, resultados, considerações finais e apêndices de integração SPTrans, planejamento de rotas e engenharia de software. Os cenários históricos de Mauá permanecem identificados; não devem ser confundidos com a implementação atual de São Paulo.

Funcionalidades documentadas: localização contínua ou simulada, enquadramento inicial de 250 m, seleção por toque prolongado, alteração de embarque preservando destino, caminhadas de até 1 km por segmento, filtro de alternativas dominadas, recálculo manual sem cache de resultados, ampulheta de carregamento, seletor Trecho, posições de ônibus e previsões por alternativa a cada 15 s, filtro de previsão incompatível com caminhada, URL raiz com precedência sobre sessão, clique externo ao painel para retornar ao mapa e agrupamento de faixas consecutivas com a mesma frequência.

Na revisão histórica de 7 de outubro, Metrô/CPTM eram evolução prevista. Em 1 de novembro, o planejamento multimodal está implementado; implantação física e avaliação sistemática com passageiros permanecem pendentes. Os testes técnicos não comprovam usabilidade nem disponibilidade operacional em todas as condições.

## Imagens e rastreabilidade

solucao_visual.tex contém capturas reais da aplicação em emulação móvel, no tema escuro, com margens de contexto nos pop-ups. imgs aponta para ../imagens. Consulte capturas/registro.csv e capturas/LEIA-ME.txt para versões, horários, dimensões e hashes. A imagem pap-02 é uma ilustração gerada por IA de uma proposta de instalação do QR Code; a captura original foi preservada em imgs/capturas_originais/pap-02-informacoes-ab32235.png. O PNG mantém a imagem gerada integralmente; o JPEG é a exportação para o PDF.

As telas foram renovadas na revisão 79dd798 e mantêm essa procedência. O complemento 4992027 acrescenta clique no fundo do painel, sem alterar a aparência das telas. Foram incluídas imagens de ônibus em aproximação e QR Code com URL na raiz. Os PNGs integrais são preservados; cinco mapas têm exportações JPEG 98/99, sem reduzir resolução ou subamostrar cores, documentadas em capturas/exportacoes-pdf.csv. As demais telas permanecem em PNG.

## Compilação

Na raiz do repositório, execute:

    latexmk -r docs/relatorio_final/.latexmkrc -cd -lualatex -interaction=nonstopmode -halt-on-error docs/relatorio_final/relatorio_final_pi2.tex

São necessários LuaLaTeX, latexmk e as fontes configuradas no preâmbulo. A disponibilidade da fonte exigida no modelo deve ser conferida antes da entrega.

gerar_pdf_envio.py copia o PDF original sem recompressão para relatorio_final_pi2_envio.pdf se o tamanho for estritamente inferior a 10.000.000 bytes. Caso exceda, a cópia de envio antiga é removida para evitar publicação equivocada. PDFs e auxiliares são ignorados pelo Git.

## Verificações e pendências

Na revisão 79dd798 passaram 154 testes de backend, 26 unitários de frontend e 64 testes de navegador, além do build. No complemento 4992027, passaram dois novos testes de clique externo e três regressões do ciclo da rota; o build também passou. Os comandos e limites da evidência constam de capturas/validacao-atual.txt e capturas/cenarios-funcionais.csv.

As pendências explícitas do texto devem ser preenchidas com informações confirmadas, incluindo link do vídeo e total definitivo de folhas. A avaliação com a comunidade permanece pendente. A captura em emulação não constitui teste em aparelho físico.
