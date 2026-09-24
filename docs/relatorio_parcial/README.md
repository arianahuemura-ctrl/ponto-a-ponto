# Relatório parcial — Projeto Integrador II

Fontes do relatório parcial do Ponto a Ponto (PaP), com as imagens e o diagrama do banco de dados utilizados no documento.

**Frase de apresentação:** “Deslocamento facilitado entre origem e destino.”

## Estrutura

- `relatorio_parcial_pi2.tex`: documento principal, referências, glossário e apêndice técnico.
- `../imagens/`: diretório central de imagens dos documentos.
- `imgs/`: link simbólico relativo para `../imagens/`.
- `../imagens/diagrama_banco.tex`: diagrama vetorial do esquema SQLite, desenhado com TikZ.

## Instalação

Em Debian/Ubuntu, os pacotes necessários à compilação podem ser instalados com:

```bash
sudo aptitude install latexmk texlive-lang-portuguese texlive-publishers texlive-latex-extra texlive-pictures lmodern
```

A classe `abntex2` faz parte de `texlive-publishers`. O relatório também utiliza TikZ, tabelas longas e URLs com quebra de linha.

## Compilação

Na raiz do repositório `ponto-a-ponto`:

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

Todas as imagens e o fonte do diagrama ficam em `docs/imagens/`. Os diretórios `docs/relatorio_parcial/imgs` e `docs/mockup/imgs` são links simbólicos relativos para `../imagens`, de modo que ambos os documentos utilizam os mesmos arquivos. Preserve os links ao copiar o projeto e recompile ambos os PDFs após alterar uma imagem. O logotipo oficial da UNIVESP é utilizado apenas na capa do relatório; sua origem está registrada em `docs/imagens/README.md`.

## Citações e referências

O relatório usa `natbib` em modo autor-data e `\citep{chave}` para chamadas entre parênteses. As referências permanecem no ambiente `thebibliography` do `.tex`, sem BibTeX, em ordem alfabética de autoria e, para uma mesma autoria, por título. Ao acrescentar uma fonte, mantenha essa ordem e o rótulo `\bibitem[{Autor}(ano)]{chave}`. Obras da mesma autoria e ano recebem letras correspondentes no rótulo e na referência (2026a, 2026b etc.). Fontes sem data identificada usam `s.d.`; a data de acesso não é usada como data de publicação.

Os intervalos da entrevista são preservados como localizadores: `\citep[181--222 s; 739--853 s]{entrevistaosmar2026}`. A ordenação e o sistema autor-data seguem a orientação e os exemplos da Live da Quinzena 4; isso não substitui a conferência dos metadados bibliográficos de cada fonte.
