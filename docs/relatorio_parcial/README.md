# Relatório parcial — Projeto Integrador II

Fontes do relatório parcial do Mauá Bus Map (MBM), com as imagens e o diagrama do banco de dados utilizados no documento.

## Estrutura

- `relatorio_parcial_pi2.tex`: documento principal, referências e apêndice técnico.
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

Esta pasta contém os arquivos necessários para compilar o relatório. O código e os dados do MBM permanecem nas respectivas pastas do mesmo projeto; a tese consultada não é necessária à compilação. A documentação das importações está em [IMPORTACOES_E_GEOLOCALIZACAO.md](../IMPORTACOES_E_GEOLOCALIZACAO.md).
