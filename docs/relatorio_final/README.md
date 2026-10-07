# Relatório final — Projeto Integrador II

Revisão de 7 de outubro de 2026. Versão da aplicação documentada: 4992027, branch sptrans. O modelo da facilitadora está em Modelo_Relatorio_Final.docx; o relatório parcial foi preservado em ../relatorio_parcial/.

## Conteúdo atual

O relatório reúne fundamentação de IHC, aplicação das disciplinas, metodologia, resultados, considerações finais e apêndices de integração SPTrans, planejamento de rotas e engenharia de software. Os cenários históricos de Mauá permanecem identificados; não devem ser confundidos com a implementação atual de São Paulo.

Funcionalidades documentadas: localização contínua ou simulada, enquadramento inicial de 250 m, seleção por toque prolongado, alteração de embarque preservando destino, caminhadas de até 1 km por segmento, filtro de alternativas dominadas, recálculo manual sem cache de resultados, ampulheta de carregamento, seletor Trecho, posições de ônibus e previsões por alternativa a cada 15 s, filtro de previsão incompatível com caminhada, URL raiz com precedência sobre sessão, clique externo ao painel para retornar ao mapa e agrupamento de faixas consecutivas com a mesma frequência.

Metrô/CPTM, implantação física e avaliação com passageiros permanecem como evoluções ou pendências. Os testes técnicos não comprovam usabilidade nem disponibilidade operacional em todas as condições.

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
