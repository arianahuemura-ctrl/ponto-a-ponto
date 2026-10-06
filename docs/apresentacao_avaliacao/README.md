# Apresentação do PaP para avaliação externa

Apresentação genérica de oito páginas para encaminhamento a profissionais de transporte público e mobilidade urbana, inclusive por vereadores e assessorias. Solicita avaliação acadêmica ou indicação de interlocutor, sem pedido de recursos, implantação, parceria ou apoio político.

## Gerar o PDF

Na raiz do repositório:

```sh
cd docs/apresentacao_avaliacao
latexmk -pdf -interaction=nonstopmode -halt-on-error Apresentacao_PaP_UNIVESP_Avaliacao.tex
```

Saída: `Apresentacao_PaP_UNIVESP_Avaliacao.pdf`. Requer os mesmos pacotes LaTeX da apresentação original (pdfLaTeX, Latin Modern, babel português, geometry, graphicx, xcolor, tabularx, enumitem, fancyhdr e hyperref). PDFs e auxiliares são ignorados pelo Git.

## Origem e preservação

Versão 2 — outubro de 2026, derivada de `../mockup/mockup_ponto_a_ponto.tex`. O documento anterior, destinado a Osmar, permanece em `../mockup/`. Esta versão tem fonte e PDF independentes e mantém as imagens originais, acessadas pelo link simbólico `imgs -> ../imagens`, sem redesenho ou cópias divergentes.

Mantidos a tipografia, cores, estrutura, oito mockups e conteúdo técnico. Alterados o destinatário, as perguntas de avaliação pertinentes, a identificação da versão e o esclarecimento do pedido acadêmico. Mauá permanece como contexto original e nas imagens ilustrativas. Dados simulados não representam integração operacional nem validação do projeto.

## Conferência da versão 2

PDF compilado e oito páginas renderizadas e inspecionadas visualmente, sem avisos de overflow. Não há referências pessoais a Osmar no texto ou nos metadados. As páginas 2, 3, 5 e 7 têm fonte idêntico ao documento original. Mauá aparece no texto apenas como contexto da operação não demonstrada e continua nas imagens originais. Não foram alterados o exemplo simulado, o algoritmo descrito ou o estágio das funcionalidades.
