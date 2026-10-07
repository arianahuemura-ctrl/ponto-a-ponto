# Relatório final — Projeto Integrador II

Revisão de 7 de outubro de 2026. Versão da aplicação documentada: b70873a, branch sptrans. O modelo da facilitadora está em Modelo_Relatorio_Final.docx; o relatório parcial foi preservado em ../relatorio_parcial/.

## Conteúdo atual

O relatório reúne fundamentação de IHC, aplicação das disciplinas, metodologia, resultados, considerações finais e apêndices de integração SPTrans, planejamento de rotas e engenharia de software. Os cenários históricos de Mauá permanecem identificados; não devem ser confundidos com a implementação atual de São Paulo.

Funcionalidades documentadas: localização contínua ou simulada, enquadramento inicial de 250 m, seleção por toque prolongado, alteração de embarque preservando destino, caminhadas de até 1 km por segmento, filtro de alternativas dominadas, recálculo manual sem cache de resultados, ampulheta de carregamento, seletor Trecho e agrupamento de faixas consecutivas com a mesma frequência.

Metrô/CPTM, implantação física e avaliação com passageiros permanecem como evoluções ou pendências. Os testes técnicos não comprovam usabilidade nem disponibilidade operacional em todas as condições.

## Imagens e rastreabilidade

solucao_visual.tex contém capturas reais da aplicação em emulação móvel, no tema escuro, com margens de contexto nos pop-ups. imgs aponta para ../imagens. Consulte capturas/registro.csv e capturas/LEIA-ME.txt para versões, horários, dimensões e hashes. A imagem pap-02 é uma ilustração gerada por IA de uma proposta de instalação do QR Code; a captura original foi preservada em imgs/capturas_originais/pap-02-informacoes-ab32235.png. O PNG mantém a imagem gerada integralmente; o JPEG é a exportação para o PDF.

As telas documentam b70873a. A captura de próximos ônibus foi refeita com o código desse commit. Os outros estados foram reutilizados de ab32235, sem alteração visual neste commit. recortes.csv e capturas_originais correspondem às imagens anteriores, não às atuais.

## Compilação

Na raiz do repositório, execute:

    latexmk -r docs/relatorio_final/.latexmkrc -cd -lualatex -interaction=nonstopmode -halt-on-error docs/relatorio_final/relatorio_final_pi2.tex

São necessários LuaLaTeX, latexmk e as fontes configuradas no preâmbulo. A disponibilidade da fonte exigida no modelo deve ser conferida antes da entrega.

gerar_pdf_envio.py copia o PDF original sem recompressão para relatorio_final_pi2_envio.pdf se o tamanho for estritamente inferior a 10.000.000 bytes. Caso exceda, a cópia de envio antiga é removida para evitar publicação equivocada. PDFs e auxiliares são ignorados pelo Git.

## Verificações e pendências

Na base ab32235 passaram 49 testes de planejamento/caminhada do backend e a verificação móvel de toque prolongado. No ajuste b70873a passaram 21 testes unitários do frontend, incluindo agrupamento de intervalos, e a compilação da aplicação.

As pendências explícitas do texto devem ser preenchidas com informações confirmadas, incluindo link do vídeo e total definitivo de folhas. A avaliação com a comunidade permanece pendente. A captura em emulação não constitui teste em aparelho físico.
