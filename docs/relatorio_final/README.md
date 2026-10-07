# Relatório final — Projeto Integrador II

Versão do relatório final preparada em 5 de outubro de 2026. A entrega parcial foi preservada em `../relatorio_parcial/`.

## Conteúdo e situação

Fundamentação, metodologia e resultados foram reorganizados em texto contínuo, com transições que identificam as etapas do Design Thinking. Foram acrescentadas considerações finais e a discussão dos registros de Santos, distinguindo resposta institucional, conversa informal e descrição de vídeo.

A avaliação do PaP com a comunidade **permanece pendente**. O grupo procura outro interlocutor diante da ausência de resposta aos contatos recentes com Osmar. Os testes de software e os relatos sobre serviços existentes não são apresentados como validação de uso. A versão deve ser complementada com os resultados reais da avaliação, as alterações motivadas pelo retorno e sua verificação, quando realizadas.

Os 88 testes citados correspondem à execução registrada em 29/09/2026 para a revisão `a60f290`; não foram reexecutados nesta alteração documental. As contagens do catálogo conservam sua data-base histórica.

## Compilação

Requer LuaLaTeX, Arial e latexmk; veja a [instalação do relatório parcial](../relatorio_parcial/README.md#instalação).

```bash
cd docs/relatorio_final
latexmk -lualatex -interaction=nonstopmode -halt-on-error relatorio_final_pi2.tex
```

PDFs e auxiliares são ignorados pelo Git. O link simbólico `imgs` aponta para `../imagens`, compartilhado com o relatório parcial e o mockup.

Para gerar o PDF de envio abaixo de 10 MB, preservando o original:

```bash
gs -sDEVICE=pdfwrite -dCompatibilityLevel=1.7 -dNOPAUSE -dBATCH -dQUIET -dDetectDuplicateImages=true -dDownsampleColorImages=true -dColorImageResolution=250 -dColorImageDownsampleType=/Bicubic -dDownsampleGrayImages=true -dGrayImageResolution=250 -dGrayImageDownsampleType=/Bicubic -dDownsampleMonoImages=true -dMonoImageResolution=300 -sOutputFile=relatorio_final_pi2_envio.pdf relatorio_final_pi2.pdf
```

## Revisão de citações e referências

- Mantidos autor-data, ordem alfabética, destaque uniforme de títulos e localizadores temporais da entrevista.
- Corrigida a autoria do estudo de Calgary para Prommaharaj e colaboradores; incluídos DOI, localização eletrônica e acesso nos artigos conferidos.
- Identificada a segunda edição de Pro Git como 2014, conforme o site oficial.
- Nos recursos digitais sem ano identificado, foi adotada a indicação editorial de século `[20--]`, em lugar de `s.d.`, conforme a possibilidade prevista no item 8.6.1.3 da NBR 6023:2025. Trata-se de inferência temporal ampla sobre documentos relativos a tecnologias/serviços deste século, não do ano de acesso usado como publicação. As letras distinguem documentos da mesma autoria e data estimada. Se surgir uma data documental mais precisa, substituí-la e conferir as citações.
- O cabeçalho HTTP Last-Modified permanece evidência de servidor na análise, não data de publicação atribuída automaticamente à referência.
- A síntese de Santos é um documento interno de 2026; não substitui a resposta original. Data e setor remetente do protocolo 7657-2026 continuam não informados.

Fontes da revisão: [orientações da USP sobre a atualização de 2025](https://www.eca.usp.br/sites/default/files/2025-06/NBR%206023_2025.pdf), [NBR 6023:2025 disponibilizada pelo Centro Paula Souza](https://bkpsitecpsnew.blob.core.windows.net/uploadsitecps/sites/149/2025/05/Referencias-NBR-6023-2025.pdf) e [orientações da UFJ sobre NBR 10520:2023](https://sibi.ufj.edu.br/apresentacao-de-citacoes-em-documentos-abnt-nbr-105202023/). A revisão não constitui certificação de conformidade pela instituição.

## Verificação desta versão

Compilação concluída com LuaLaTeX: 64 páginas, sem citações/remissões indefinidas nem caixas excedendo as margens. Conferidas 35 referências, todas citadas, e ausência de subdivisões internas nas três seções revisadas. A versão compacta tem aproximadamente 2,66 MB; a comparação do texto extraído confirmou as mesmas palavras em cada página dos dois PDFs. Arial está incorporada. Houve inspeção visual do resumo, tabela e referências. O motor ainda registra avisos de comandos obsoletos e ajuste de espaço em tabelas longas, sem interrupção da compilação.
