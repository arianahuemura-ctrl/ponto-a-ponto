# Relatório parcial — Projeto Integrador II

Fontes do relatório parcial do Ponto a Ponto (PaP), com as imagens e o diagrama do banco de dados utilizados no documento.

**Frase de apresentação:** “Deslocamento facilitado entre origem e destino.”

## Estrutura

- `relatorio_parcial_pi2.tex`: documento principal, referências, glossário e apêndice técnico.
- `imgs/`: imagens efetivamente referenciadas pelo relatório.
- `imgs/diagrama_banco.tex`: diagrama vetorial do esquema SQLite, desenhado com TikZ.

## Instalação

Em Debian/Ubuntu, os pacotes necessários à compilação podem ser instalados com:

```bash
sudo aptitude install latexmk texlive-lang-portuguese texlive-publishers texlive-latex-extra texlive-pictures lmodern
```

A classe `abntex2` faz parte de `texlive-publishers`. O relatório também utiliza TikZ, tabelas longas e URLs com quebra de linha.

## Compilação

Na raiz do repositório `maua_bus_map`:

```bash
cd docs/relatorio_parcial
latexmk -pdf -interaction=nonstopmode -halt-on-error relatorio_parcial_pi2.tex
```

O resultado é `relatorio_parcial_pi2.pdf`. O PDF e os arquivos auxiliares são gerados localmente e ignorados pelo Git.

## Desenvolvimento

Edite os arquivos desta pasta (`docs/relatorio_parcial`) para registrar as próximas alterações no Git da própria aplicação. Não há um repositório Git separado dentro dela. As cópias anteriores na pasta PI2 foram preservadas e não são sincronizadas automaticamente.

As mensagens dos commits devem ser escritas em português. Os mockups e dados simulados devem permanecer identificados como ilustrativos; a origem das capturas e os limites dos dados estão documentados no relatório.

Esta pasta contém os arquivos necessários para compilar o relatório. O código e os dados do Ponto a Ponto (PaP) permanecem nas respectivas pastas do mesmo projeto; a tese consultada não é necessária à compilação. A documentação das importações está em [IMPORTACOES_E_GEOLOCALIZACAO.md](../IMPORTACOES_E_GEOLOCALIZACAO.md).

## Imagens compartilhadas com a apresentação

As imagens `imgs/mockup1.png` a `imgs/mockup8.png` são a fonte única para este relatório e para `../mockup/mockup_ponto_a_ponto.tex`. O diretório `../mockup/imgs` é um link simbólico relativo para `imgs` deste relatório. Após editar uma tela, recompile ambos os documentos para atualizar os PDFs.

## Citações e referências

O relatório usa `natbib` em modo autor-data e `\citep{chave}` para chamadas entre parênteses. As referências permanecem no ambiente `thebibliography` do `.tex`, sem BibTeX, em ordem alfabética de autoria e, para uma mesma autoria, por título. Ao acrescentar uma fonte, mantenha essa ordem e o rótulo `\bibitem[{Autor}(ano)]{chave}`. Obras da mesma autoria e ano recebem letras correspondentes no rótulo e na referência (2026a, 2026b etc.). Fontes sem data identificada usam `s.d.`; a data de acesso não é usada como data de publicação.

Os intervalos da entrevista são preservados como localizadores: `\citep[181--222 s; 739--853 s]{entrevistaosmar2026}`. A ordenação e o sistema autor-data seguem a orientação e os exemplos da Live da Quinzena 4; isso não substitui a conferência dos metadados bibliográficos de cada fonte.
