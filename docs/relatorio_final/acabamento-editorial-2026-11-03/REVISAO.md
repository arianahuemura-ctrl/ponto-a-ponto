# Acabamento editorial mínimo — 03/11/2026

Referência: branch relatorio, HEAD aef369c. Sem commit automático.

- Introdução: “na Apêndice A” → “no Apêndice A”.
- Fundamentação: “na Seção A” → “no Apêndice A”. O destino `sec:implementar-testar` está dentro do Apêndice A e foi mantido.
- Títulos de seções/subseções: quebra entre palavras, sem hifenização; alinhamento à esquerda. Conferidos visualmente 3.6 e H.4 (páginas impressas 61 e 149; físicas 69 e 157).

LuaLaTeX via latexmk -norc, compilação final com saída 0; 167 páginas antes e depois. Zero Overfull e referências indefinidas na compilação final. Permanecem avisos Underfull e compatibilidade do modelo. A primeira tentativa sem alinhamento à esquerda produziu dois Overfull, resolvidos na segunda.

Comparação por página, normalizando espaços e hifenização: únicas mudanças textuais nas páginas físicas 9 e 16, correspondentes às duas correções acima. Sumário e listas (páginas pré-textuais 4–8) idênticos. Marcadores e URIs preservados: 64 e 84. Link definitivo preservado: https://www.youtube.com/watch?v=rSvuIWx8QAg (mesmo vídeo de https://youtu.be/rSvuIWx8QAg).

Parecer assinado: seis páginas finais renderizadas a 100 dpi idênticas pixel a pixel entre o PDF anterior e a nova compilação. Documento original e inclusão integral não editados; nenhuma assinatura extraída ou reutilizada. Conteúdo, resultados quantitativos, autoria, avaliação externa, conclusões e limites metodológicos preservados.

Entregas: PDF compilado `PaP_relatorio_2026-11-03_acabamento.pdf` e cópia para upload `PaP_relatorio_2026-11-03_ENTREGA_revisada.pdf`, também em Downloads. Esta última tem 4.897.140 bytes, abaixo de 10 MB, com a mesma compressão da entrega anterior (imagens 220 dpi/JPEG 95; monocromáticas 400 dpi). Texto da compactação idêntico à compilação. Renderização das 167 páginas aprovada. Originais preservados. Hashes em validacao.json; original_sha256 nesse JSON refere-se à nova compilação antes da compactação.

Logs e evidências: `.cache/setup/acabamento-editorial-20261103/`, especialmente build-2.log, validation.log e antes/depois-parecer.log. Não houve upload institucional nem testes do aplicativo.
