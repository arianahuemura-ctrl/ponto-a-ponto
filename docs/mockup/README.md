# Apresentação do Ponto a Ponto a Osmar

Documento de oito páginas para apresentar o fluxo conceitual e solicitar sugestões da comunidade externa. As oito imagens são acessadas por `imgs`, um link simbólico relativo para `../imagens/`. O relatório e esta apresentação usam os mesmos arquivos, sem cópias independentes. Edite as imagens no diretório central `docs/imagens/` e recompile os dois PDFs. Mantenha essa estrutura e preserve links simbólicos ao clonar ou copiar o projeto.

## Gerar o PDF

Na raiz do repositório:

```sh
cd docs/mockup
latexmk -pdf -interaction=nonstopmode -halt-on-error mockup_ponto_a_ponto.tex
```

O arquivo resultante é `mockup_ponto_a_ponto.pdf`. PDFs e arquivos auxiliares são ignorados pelo Git localmente.

## Enviar e registrar o retorno

Use o texto de `email_osmar.md` e anexe o PDF gerado. O e-mail não foi enviado automaticamente. Registre a data do envio, a versão apresentada, o retorno efetivamente recebido e as alterações decorrentes antes de atualizar o relatório sobre a avaliação da comunidade.

As imagens são conceituais e usam o nome “Ponto a Ponto”. Tempos, locais e posições são ilustrativos; não são capturas do protótipo nem dados operacionais validados. O exemplo de baldeação é independente dos valores desenhados nas imagens.

## Edição da identidade visual

As telas `mockup2.png` a `mockup8.png` foram editadas com a ferramenta integrada `imagegen`. Instrução utilizada em cada tela: substituir apenas o título “Meu Ponto” por “Ponto a Ponto”, mantendo a tipografia azul, o enquadramento e os demais elementos. A imagem da placa (`mockup1.png`) foi preservada. Por serem imagens geradas, permanecem referências conceituais, não capturas do software.
